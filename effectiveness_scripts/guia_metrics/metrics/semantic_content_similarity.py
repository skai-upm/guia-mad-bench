from __future__ import annotations

from pathlib import Path
import math
import warnings
from typing import Any

from guia_metrics.common import parse_graph, literals_by_property, mean, std


METRIC_NAME = "semantic_content_similarity"

CANONICAL_METHODS = ("sentence_bert", "bertscore")
_FACTORY_CACHE: dict[Any, Any] = {}
_FACTORY_ERRORS: dict[Any, str] = {}


def _normalise_methods(semantic_methods: str | None) -> list[str]:
    if not semantic_methods:
        return list(CANONICAL_METHODS)
    raw = [m.strip() for m in str(semantic_methods).split(",") if m.strip()]
    if not raw or raw == ["all"]:
        return list(CANONICAL_METHODS)
    if raw == ["none"]:
        return []
    expanded = []
    for m in raw:
        if m == "all":
            expanded.extend(CANONICAL_METHODS)
        elif m != "none":
            expanded.append(m)
    return list(dict.fromkeys(expanded))


def _clean_literals_by_property(values: dict[Any, list[str]]) -> dict[Any, list[str]]:
    """Remove empty/blank literals before semantic scoring.

    BERTScore warns repeatedly when a candidate sentence is empty. In this
    benchmark, empty strings normally correspond to empty generated literals,
    not meaningful semantic content. We treat them as missing values and let the
    property-level score become 0.0 when either side has no usable literal.
    """
    cleaned: dict[Any, list[str]] = {}
    for prop, literals in values.items():
        usable = []
        for lit in literals:
            text = str(lit).strip()
            if text:
                usable.append(text)
        if usable:
            cleaned[prop] = usable
    return cleaned


def _cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _sample_expected(expected: list[str], max_expected: int) -> list[str]:
    """Deterministically sample expected literals when a speed cap is enabled."""
    if max_expected <= 0 or len(expected) <= max_expected:
        return expected
    step = max(1, len(expected) // max_expected)
    sampled = expected[::step][:max_expected]
    return sampled or expected[:max_expected]


def _property_scores_pairwise(
    pred_lits: dict[Any, list[str]],
    gold_lits: dict[Any, list[str]],
    similarity_fn,
    max_pairs_per_property: int = 0,
) -> list[float]:
    """Generic exact/approximate pairwise property scoring.

    For each predicted literal, its score is the maximum similarity against the
    expected literals of the same property. If max_pairs_per_property > 0, the
    expected literals are deterministically downsampled to keep runtime bounded.
    """
    properties = set(pred_lits) | set(gold_lits)
    scores = []

    for prop in properties:
        predicted = pred_lits.get(prop, [])
        expected = gold_lits.get(prop, [])

        if not predicted or not expected:
            scores.append(0.0)
            continue

        expected_for_prop = expected
        if max_pairs_per_property > 0 and len(predicted) * len(expected) > max_pairs_per_property:
            max_expected = max(1, max_pairs_per_property // max(1, len(predicted)))
            expected_for_prop = _sample_expected(expected, max_expected)

        lit_scores = []
        for lit in predicted:
            lit_scores.append(max(similarity_fn(lit, exp) for exp in expected_for_prop))
        scores.append(sum(lit_scores) / len(lit_scores))

    return scores


def _sentence_bert_similarity_factory(model_name: str, batch_size: int):
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    cache: dict[str, list[float]] = {}

    def embed_many(texts: list[str]) -> None:
        missing = [t for t in dict.fromkeys(texts) if t not in cache]
        if not missing:
            return
        vectors = model.encode(
            missing,
            normalize_embeddings=True,
            batch_size=batch_size,
            show_progress_bar=False,
        )
        for text, vector in zip(missing, vectors):
            cache[text] = vector.tolist()

    def sim(a: str, b: str) -> float:
        embed_many([a, b])
        return _cosine(cache[a], cache[b])

    return sim


def _bertscore_scorer_factory(lang: str = "es", batch_size: int = 32):
    from bert_score import BERTScorer

    # Keep the model loaded. Calling bert_score.score repeatedly is much slower
    # because it may reload/reinitialise more internals.
    scorer = BERTScorer(lang=lang, rescale_with_baseline=False)

    def score_pairs(cands: list[str], refs: list[str]) -> list[float]:
        if not cands:
            return []
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*Empty candidate sentence.*")
            _, _, f1 = scorer.score(cands, refs, batch_size=batch_size, verbose=False)
        return [float(x) for x in f1]

    return score_pairs


def _factory_key(method: str, sentence_model: str, bertscore_lang: str, batch_size: int):
    if method == "sentence_bert":
        return (method, sentence_model, batch_size)
    if method == "bertscore":
        return (method, bertscore_lang, batch_size)
    return (method,)


def _get_similarity_factory(
    method: str,
    sentence_model: str,
    bertscore_lang: str,
    batch_size: int,
):
    key = _factory_key(method, sentence_model, bertscore_lang, batch_size)
    if key in _FACTORY_CACHE:
        return _FACTORY_CACHE[key]
    if key in _FACTORY_ERRORS:
        raise RuntimeError(_FACTORY_ERRORS[key])

    factories = {
        "sentence_bert": lambda: _sentence_bert_similarity_factory(sentence_model, batch_size),
        "bertscore": lambda: _bertscore_scorer_factory(bertscore_lang, batch_size),
    }
    if method not in factories:
        raise ValueError(f"Unknown semantic method '{method}'")

    try:
        _FACTORY_CACHE[key] = factories[method]()
        return _FACTORY_CACHE[key]
    except Exception as exc:
        _FACTORY_ERRORS[key] = str(exc)
        raise


def _bertscore_property_scores(
    pred_lits: dict[Any, list[str]],
    gold_lits: dict[Any, list[str]],
    score_pairs_fn,
    max_pairs_per_property: int = 0,
) -> list[float]:
    """Batched BERTScore property scoring.

    BERTScore is expensive. This implementation batches all candidate-reference
    comparisons for one property at a time instead of invoking the scorer once
    per pair.
    """
    properties = set(pred_lits) | set(gold_lits)
    scores = []

    for prop in properties:
        predicted = pred_lits.get(prop, [])
        expected = gold_lits.get(prop, [])

        if not predicted or not expected:
            scores.append(0.0)
            continue

        expected_for_prop = expected
        if max_pairs_per_property > 0 and len(predicted) * len(expected) > max_pairs_per_property:
            max_expected = max(1, max_pairs_per_property // max(1, len(predicted)))
            expected_for_prop = _sample_expected(expected, max_expected)

        cands = []
        refs = []
        owner_indexes = []
        for i, cand in enumerate(predicted):
            for ref in expected_for_prop:
                cands.append(cand)
                refs.append(ref)
                owner_indexes.append(i)

        pair_scores = score_pairs_fn(cands, refs)
        best = [0.0] * len(predicted)
        for i, pair_score in zip(owner_indexes, pair_scores):
            if pair_score > best[i]:
                best[i] = pair_score

        scores.append(sum(best) / len(best))

    return scores


def compute(
    pred_file: str | Path,
    gold_file: str | Path,
    ontology_graph=None,
    logger=None,
    rdf_format="turtle",
    semantic_methods: str = "sentence_bert,bertscore",
    sentence_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    bertscore_lang: str = "es",
    semantic_batch_size: int = 32,
    semantic_max_pairs_per_property: int = 0,
    **kwargs,
):
    try:
        pred = parse_graph(pred_file, rdf_format)
        gold = parse_graph(gold_file, rdf_format)
    except Exception as e:
        if logger:
            logger.log(
                METRIC_NAME,
                "Semantic content similarity could not parse RDF files.",
                pred_file=str(pred_file),
                gold_file=str(gold_file),
                exception=e,
            )
        return _empty_result(semantic_methods)

    requested = _normalise_methods(semantic_methods)
    if not requested:
        return {}

    pred_lits = _clean_literals_by_property(literals_by_property(pred))
    gold_lits = _clean_literals_by_property(literals_by_property(gold))
    result = {}

    for method in requested:
        try:
            scorer = _get_similarity_factory(
                method,
                sentence_model,
                bertscore_lang,
                int(semantic_batch_size),
            )

            if method == "bertscore":
                scores = _bertscore_property_scores(
                    pred_lits,
                    gold_lits,
                    scorer,
                    max_pairs_per_property=int(semantic_max_pairs_per_property),
                )
            else:
                scores = _property_scores_pairwise(
                    pred_lits,
                    gold_lits,
                    scorer,
                    max_pairs_per_property=int(semantic_max_pairs_per_property),
                )

            result[f"sem_lex_{method}_avg"] = mean(scores)
            result[f"sem_lex_{method}_std"] = std(scores)

        except Exception as e:
            if logger:
                logger.log(
                    METRIC_NAME,
                    f"Semantic method '{method}' failed. Values left empty. "
                    "Install the optional semantic dependencies and required models to compute this method.",
                    pred_file=str(pred_file),
                    gold_file=str(gold_file),
                    exception=e,
                )
            result[f"sem_lex_{method}_avg"] = None
            result[f"sem_lex_{method}_std"] = None

    return result


def _empty_result(semantic_methods: str):
    return {
        f"sem_lex_{method}_{suffix}": None
        for method in _normalise_methods(semantic_methods)
        for suffix in ("avg", "std")
    }
