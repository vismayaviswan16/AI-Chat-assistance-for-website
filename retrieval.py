"""Finds the knowledge chunks that best match a visitor's question.

Two modes, chosen by EMBED_PROVIDER in .env:

  * embedding - compares meaning using any embedding model (Ollama, OpenAI, Gemini...)
  * keyword   - classic BM25 word matching. Needs no AI model and no extra setup, so it
                works with any chat provider (including ones without an embeddings API).
                It matches words, not meaning: "price" won't find a chunk that only says
                "cost", so write your knowledge files with the words visitors will use.
"""
import math
import re

STOPWORDS = set(
    "a an and are as at be been but by can could do does for from had has have how i if in "
    "is it its me my of on or our so that the their them there these they this to us was we "
    "were what when where which who why will with would you your".split()
)


def _stem(word):
    """Very light plural handling so 'services' matches 'service'."""
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


FOLLOW_UP_WORDS = {"that", "it", "this", "those", "them", "they", "there", "one", "ones", "also", "too"}


def is_follow_up(message):
    """True for short messages that only make sense with the previous question ("how much is that?")."""
    words = re.findall(r"[a-z']+", message.lower())
    content = [w for w in words if w not in STOPWORDS]
    return not content or bool(set(words) & FOLLOW_UP_WORDS)


def tokenize(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [_stem(w) for w in words if w not in STOPWORDS and len(w) > 1]


class KeywordIndex:
    """BM25 ranking plus an idf-weighted 'coverage' score (0..1) used as the relevance cut-off."""

    K1 = 1.5
    B = 0.75

    def __init__(self, entries):
        self.entries = entries
        self.docs = [tokenize(e["text"]) for e in entries]
        self.n = len(self.docs)
        self.avg_len = (sum(len(d) for d in self.docs) / self.n) if self.n else 0
        self.df = {}
        for doc in self.docs:
            for term in set(doc):
                self.df[term] = self.df.get(term, 0) + 1
        self.tf = []
        for doc in self.docs:
            counts = {}
            for term in doc:
                counts[term] = counts.get(term, 0) + 1
            self.tf.append(counts)

    def _idf(self, term):
        df = self.df.get(term, 0)
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def search(self, query, top_k, min_coverage):
        terms = set(tokenize(query))
        if not terms or not self.n:
            return []
        idf = {t: self._idf(t) for t in terms}
        # Words that appear nowhere in the knowledge base count half, so one off-topic or
        # differently-worded word doesn't veto an otherwise good match.
        weight = {t: idf[t] * (1.0 if t in self.df else 0.5) for t in terms}
        total_weight = sum(weight.values()) or 1.0

        results = []
        for i, counts in enumerate(self.tf):
            matched = [t for t in terms if t in counts]
            if not matched:
                continue
            length_norm = 1 - self.B + self.B * (len(self.docs[i]) / (self.avg_len or 1))
            bm25 = sum(
                idf[t] * counts[t] * (self.K1 + 1) / (counts[t] + self.K1 * length_norm)
                for t in matched
            )
            coverage = sum(weight[t] for t in matched) / total_weight
            if coverage >= min_coverage:
                results.append({**self.entries[i], "score": coverage, "_rank": bm25})

        results.sort(key=lambda r: r["_rank"], reverse=True)
        return results[:top_k]


class Retriever:
    def __init__(self, entries, embedder, top_k, min_score, min_coverage):
        self.embedder = embedder
        self.top_k = top_k
        self.min_score = min_score
        self.min_coverage = min_coverage
        self.entries = entries

        if embedder is None:
            self.keyword = KeywordIndex(entries)
        else:
            self.keyword = None
            for e in entries:  # pre-compute vector lengths once instead of on every request
                e["norm"] = math.sqrt(sum(x * x for x in e["embedding"]))

    def search(self, query):
        if self.keyword is not None:
            return self.keyword.search(query, self.top_k, self.min_coverage)

        qvec = self.embedder.embed([query], kind="query")[0]
        qnorm = math.sqrt(sum(x * x for x in qvec))
        if qnorm == 0:
            return []
        scored = []
        for item in self.entries:
            if item["norm"] == 0:
                continue
            dot = sum(x * y for x, y in zip(qvec, item["embedding"]))
            scored.append({**item, "score": dot / (qnorm * item["norm"])})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return [c for c in scored[: self.top_k] if c["score"] >= self.min_score]
