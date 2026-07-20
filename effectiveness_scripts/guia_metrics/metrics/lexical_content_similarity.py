from __future__ import annotations

from pathlib import Path
from collections import Counter
import math
import re

from guia_metrics.common import parse_graph, literals_by_property, mean, std


METRIC_NAME = "lexical_content_similarity"


_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def jaccard(a: str, b: str) -> float:
    sa, sb = set(tokens(a)), set(tokens(b))
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def levenshtein_similarity(a: str, b: str) -> float:
    try:
        import Levenshtein  # type: ignore
        distance = Levenshtein.distance(a, b)
    except Exception:
        distance = _levenshtein_distance(a, b)
    max_len = max(len(a), len(b))
    if max_len == 0:
        return 1.0
    return 1.0 - (distance / max_len)


def _levenshtein_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) < len(b):
        return _levenshtein_distance(b, a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            insert = current[j - 1] + 1
            delete = previous[j] + 1
            replace = previous[j - 1] + (ca != cb)
            current.append(min(insert, delete, replace))
        previous = current
    return previous[-1]


def cosine_counter(ca: Counter, cb: Counter) -> float:
    if not ca and not cb:
        return 1.0
    if not ca or not cb:
        return 0.0
    inter = set(ca) & set(cb)
    dot = sum(ca[t] * cb[t] for t in inter)
    na = math.sqrt(sum(v * v for v in ca.values()))
    nb = math.sqrt(sum(v * v for v in cb.values()))
    return dot / (na * nb) if na and nb else 0.0


def bow_cosine(a: str, b: str) -> float:
    return cosine_counter(Counter(tokens(a)), Counter(tokens(b)))


def tfidf_cosine(a: str, b: str) -> float:
    # Use sklearn when available. Fall back to a small two-document TF-IDF implementation.
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        vec = TfidfVectorizer().fit_transform([a, b])
        return float(cosine_similarity(vec[0], vec[1])[0][0])
    except Exception:
        docs = [tokens(a), tokens(b)]
        vocab = sorted(set(docs[0]) | set(docs[1]))
        if not vocab:
            return 1.0
        vectors = []
        for doc in docs:
            tf = Counter(doc)
            v = []
            for term in vocab:
                df = sum(1 for d in docs if term in d)
                idf = math.log((1 + len(docs)) / (1 + df)) + 1
                v.append(tf[term] * idf)
            vectors.append(Counter({term: val for term, val in zip(vocab, v) if val}))
        return cosine_counter(vectors[0], vectors[1])


STRATEGIES = {
    "jaccard": jaccard,
    "levenshtein": levenshtein_similarity,
    "tfidf_cosine": tfidf_cosine,
    "bow_cosine": bow_cosine,
}


def _property_scores(pred_lits: dict, gold_lits: dict, similarity_fn) -> list[float]:
    properties = set(pred_lits) | set(gold_lits)
    scores = []
    for p in properties:
        predicted = pred_lits.get(p, [])
        expected = gold_lits.get(p, [])
        if not predicted:
            scores.append(0.0)
            continue
        if not expected:
            scores.append(0.0)
            continue
        lit_scores = []
        for lit in predicted:
            lit_scores.append(max(similarity_fn(lit, exp) for exp in expected))
        scores.append(sum(lit_scores) / len(lit_scores))
    return scores


def compute(pred_file: str | Path, gold_file: str | Path, ontology_graph=None, logger=None, rdf_format="turtle", **kwargs):
    try:
        pred = parse_graph(pred_file, rdf_format)
        gold = parse_graph(gold_file, rdf_format)
        pred_lits = literals_by_property(pred)
        gold_lits = literals_by_property(gold)
        result = {}
        for name, fn in STRATEGIES.items():
            scores = _property_scores(pred_lits, gold_lits, fn)
            result[f"fuzzy_lex_{name}_avg"] = mean(scores)
            result[f"fuzzy_lex_{name}_std"] = std(scores)
        return result
    except Exception as e:
        if logger:
            logger.log(METRIC_NAME, "Lexical content similarity metric failed.",
                       pred_file=str(pred_file), gold_file=str(gold_file), exception=e)
        return {f"fuzzy_lex_{name}_{suffix}": None for name in STRATEGIES for suffix in ("avg", "std")}
