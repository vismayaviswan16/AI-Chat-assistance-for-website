import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
import ollama

load_dotenv()

BASE_DIR = Path(__file__).parent
KB_DIR = BASE_DIR / "knowledge"
OUTPUT_FILE = BASE_DIR / "index.json"

# OPTIONAL: must be the same model server.py uses.
# Change it in your .env file (EMBED_MODEL=...), not here.
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")


def build_index():
    # Only .txt files are read, so knowledge/README.md is ignored.
    files = sorted(KB_DIR.glob("*.txt"))

    if not files:
        print(f"No .txt files found in {KB_DIR}")
        sys.exit(1)

    print(f"Found {len(files)} knowledge files. Embedding with Ollama ({EMBED_MODEL})...")
    index = []

    for f in files:
        text = f.read_text(encoding="utf-8").strip()
        if not text:
            continue

        result = ollama.embeddings(model=EMBED_MODEL, prompt=text)

        index.append({"file": f.name, "text": text, "embedding": result["embedding"]})
        print(f"  embedded: {f.name}")

        time.sleep(0.3)

    OUTPUT_FILE.write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"\nDone. Saved {len(index)} entries to {OUTPUT_FILE}")


if __name__ == "__main__":
    try:
        build_index()
    except Exception as exc:  # noqa: BLE001
        print(f"Embedding failed: {exc}")
        sys.exit(1)