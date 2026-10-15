"""Builds index.json from the .txt files in the knowledge/ folder.

Run this once, and again whenever you change a knowledge file or change
EMBED_PROVIDER / EMBED_MODEL in .env:

    python embed.py

Long files are split into small overlapping chunks. This matters: one huge
embedding per file gets truncated by the model and matches questions poorly.

With EMBED_PROVIDER=keyword no AI model is used at all - the chunks are simply
saved and searched by keyword.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from providers import ProviderError, build_embedder, embed_settings  # noqa: E402

BASE_DIR = Path(__file__).parent
KB_DIR = BASE_DIR / "knowledge"
OUTPUT_FILE = BASE_DIR / "index.json"

# OPTIONAL (in .env): chunk size and overlap, in characters.
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "16"))


def split_long(paragraph, size):
    """Split one very long paragraph at sentence boundaries."""
    parts, current = [], ""
    for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
        while len(sentence) > size:  # a single enormous sentence: hard split
            if current:
                parts.append(current)
                current = ""
            parts.append(sentence[:size])
            sentence = sentence[size:]
        if current and len(current) + 1 + len(sentence) > size:
            parts.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        parts.append(current)
    return parts


def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Group paragraphs into chunks of about `size` characters with a small overlap."""
    pieces = []
    for paragraph in (p.strip() for p in re.split(r"\n\s*\n", text)):
        if not paragraph:
            continue
        pieces.extend(split_long(paragraph, size) if len(paragraph) > size else [paragraph])

    chunks, current = [], ""
    for piece in pieces:
        if current and len(current) + 2 + len(piece) > size:
            chunks.append(current)
            tail = current[-overlap:] if overlap > 0 else ""
            if " " in tail:
                tail = tail[tail.find(" ") + 1:]  # start the overlap on a whole word
            current = f"{tail}\n\n{piece}" if tail else piece
        else:
            current = f"{current}\n\n{piece}" if current else piece
    if current:
        chunks.append(current)
    return chunks


def embed_batch_with_retry(embedder, texts, attempts=3):
    for attempt in range(1, attempts + 1):
        try:
            return embedder.embed(texts, kind="document")
        except Exception:  # noqa: BLE001
            if attempt == attempts:
                raise
            time.sleep(2 * attempt)


def build_index():
    provider, model = embed_settings()
    embedder, label = build_embedder()

    # Only .txt files are read, so knowledge/README.md is ignored.
    files = sorted(KB_DIR.glob("*.txt"))
    if not files:
        print(f"No .txt files found in {KB_DIR}")
        sys.exit(1)

    print(f"Found {len(files)} knowledge files. Indexing with: {label}")

    entries = []
    for f in files:
        text = f.read_text(encoding="utf-8").strip()
        if not text:
            print(f"  skipped (empty): {f.name}")
            continue
        chunks = chunk_text(text)
        for start in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[start:start + BATCH_SIZE]
            vectors = embed_batch_with_retry(embedder, batch) if embedder else [None] * len(batch)
            for offset, (chunk, vector) in enumerate(zip(batch, vectors), start=start + 1):
                entry = {"file": f.name, "chunk": offset, "text": chunk}
                if vector is not None:
                    entry["embedding"] = vector
                entries.append(entry)
        print(f"  indexed: {f.name} ({len(chunks)} chunk{'s' if len(chunks) != 1 else ''})")

    if not entries:
        print("Nothing to index - all knowledge files were empty.")
        sys.exit(1)

    index = {
        "embed_provider": provider,
        "embed_model": model,
        "chunk_size": CHUNK_SIZE,
        "entries": entries,
    }

    # Write to a temporary file first so a crash can never leave a half-written index.json.
    tmp = OUTPUT_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(index, separators=(",", ":")), encoding="utf-8")
    tmp.replace(OUTPUT_FILE)
    print(f"\nDone. Saved {len(entries)} chunks to {OUTPUT_FILE}")


if __name__ == "__main__":
    try:
        build_index()
    except ProviderError as exc:
        print(f"Setup problem: {exc}")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"Indexing failed: {exc}")
        print("Check that your provider is reachable, your API key is valid and EMBED_MODEL exists.")
        sys.exit(1)
