from __future__ import annotations

import csv
import math
from pathlib import Path
from statistics import median
from typing import Any

from guia_metrics.common import clean_float


def _to_float(value):
    if value in ("", None):
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, str):
        if value.lower() == "true":
            return 1.0
        if value.lower() == "false":
            return 0.0
    try:
        return float(value)
    except Exception:
        return None


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    vals = sorted(values)
    k = (len(vals) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return clean_float(vals[int(k)])
    return clean_float(vals[f] * (c - k) + vals[c] * (k - f))




ID_COLUMNS = ("file", "pred_file", "gold_file")

STRUCTURAL_DOCUMENT_COLUMNS = [
    "file",
    "pred_file",
    "gold_file",
    "syntactic_consistency",
    "ontology_conformance",
    "class_hallucination",
    "property_hallucination",
    "hallucinated_classes",
    "hallucinated_properties",
]

STRICT_DOCUMENT_COLUMNS = [
    "file",
    "pred_file",
    "gold_file",
    "expected_typed_instances",
    "typed_instances_pred",
    "typed_instances_gold",
    "expected_properties",
    "properties_pred",
    "properties_gold",
    "expected_datatype_literals",
    "datatype_literals_pred",
    "datatype_literals_gold",
    "expected_language_tagged_literals",
    "language_tagged_literals_pred",
    "language_tagged_literals_gold",
    "strict_precision",
    "strict_recall",
    "strict_f1",
    "strict_accuracy",
    "strict_tp",
    "strict_fp",
    "strict_fn",
    "strict_tn",
]

FUZZY_DOCUMENT_COLUMNS = [
    "file",
    "pred_file",
    "gold_file",
    "fuzzy_lex_jaccard_avg",
    "fuzzy_lex_jaccard_std",
    "fuzzy_lex_levenshtein_avg",
    "fuzzy_lex_levenshtein_std",
    "fuzzy_lex_tfidf_cosine_avg",
    "fuzzy_lex_tfidf_cosine_std",
    "fuzzy_lex_bow_cosine_avg",
    "fuzzy_lex_bow_cosine_std",
    "sem_lex_sentence_bert_avg",
    "sem_lex_sentence_bert_std",
    "sem_lex_bertscore_avg",
    "sem_lex_bertscore_std",
]

# Final metrics shown in compact summaries.
STRICT_FINAL_METRICS = [
    "expected_typed_instances",
    "expected_properties",
    "expected_datatype_literals",
    "expected_language_tagged_literals",
    "strict_precision",
    "strict_recall",
    "strict_f1",
    "strict_accuracy",
]

FUZZY_FINAL_METRICS = [
    "fuzzy_lex_jaccard_avg",
    "fuzzy_lex_levenshtein_avg",
    "fuzzy_lex_tfidf_cosine_avg",
    "fuzzy_lex_bow_cosine_avg",
    "sem_lex_sentence_bert_avg",
    "sem_lex_bertscore_avg",
]


def _read_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_rows(rows: list[dict[str, Any]], path: str | Path, fieldnames: list[str] | None = None) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for k in row:
                if k not in fieldnames:
                    fieldnames.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def _project_rows(rows: list[dict[str, Any]], columns: list[str]) -> list[dict[str, Any]]:
    present = []
    for col in columns:
        if any(col in row for row in rows):
            present.append(col)
    return [{col: row.get(col, "") for col in present} for row in rows]


def _is_true(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def _is_false(value: Any) -> bool:
    return str(value).strip().lower() == "false"


def _numeric_values(rows: list[dict[str, Any]], metric: str) -> list[float]:
    vals: list[float] = []
    for row in rows:
        v = _to_float(row.get(metric))
        if v is not None and not math.isnan(v):
            vals.append(v)
    return vals


def _continuous_summary(rows: list[dict[str, Any]], metrics: list[str]) -> list[dict[str, Any]]:
    out = []
    n_docs = len(rows)
    for metric in metrics:
        values = _numeric_values(rows, metric)
        if not values:
            continue
        m = clean_float(sum(values) / len(values))
        out.append({
            "metric": metric,
            "documents_total": n_docs,
            "documents_with_value": len(values),
            "coverage": clean_float(len(values) / n_docs) if n_docs else "",
            "mean": m,
            "std": clean_float(math.sqrt(sum((v - m) ** 2 for v in values) / len(values))),
            "min": clean_float(min(values)),
            "p25": percentile(values, 0.25),
            "median": clean_float(median(values)),
            "p75": percentile(values, 0.75),
            "p90": percentile(values, 0.90),
            "p95": percentile(values, 0.95),
            "max": clean_float(max(values)),
        })
    return out


def structural_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    n = len(rows)
    out: list[dict[str, Any]] = []

    for metric in ("syntactic_consistency", "ontology_conformance"):
        values = [row.get(metric, "") for row in rows if metric in row]
        passed = sum(1 for v in values if _is_true(v))
        failed = sum(1 for v in values if _is_false(v))
        missing = n - len(values)
        out.append({
            "metric": metric,
            "documents_total": n,
            "passed": passed,
            "failed": failed,
            "missing": missing,
            "success_rate": clean_float(passed / n) if n else "",
            "failure_rate": clean_float(failed / n) if n else "",
        })

    for metric in ("class_hallucination", "property_hallucination"):
        values = _numeric_values(rows, metric)
        total_errors = sum(values)
        docs_with_errors = sum(1 for v in values if v > 0)
        out.append({
            "metric": metric,
            "documents_total": n,
            "documents_with_value": len(values),
            "documents_with_errors": docs_with_errors,
            "documents_without_errors": len(values) - docs_with_errors,
            "error_free_rate": clean_float((len(values) - docs_with_errors) / n) if n else "",
            "total_errors": clean_float(total_errors),
            "mean_errors_per_document": clean_float(total_errors / n) if n else "",
            "max_errors_in_document": clean_float(max(values)) if values else "",
        })

    # Overall syntactic failure rate for quick paper reporting.
    if rows and any("syntactic_consistency" in row for row in rows):
        failed = sum(1 for row in rows if _is_false(row.get("syntactic_consistency", "")))
        out.append({
            "metric": "failure_rate",
            "documents_total": n,
            "failed": failed,
            "success_rate": clean_float(1 - failed / n) if n else "",
            "failure_rate": clean_float(failed / n) if n else "",
        })

    return out


def strict_content_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = _continuous_summary(rows, STRICT_FINAL_METRICS)
    n = len(rows)

    tp = sum(_to_float(r.get("strict_tp")) or 0 for r in rows)
    fp = sum(_to_float(r.get("strict_fp")) or 0 for r in rows)
    fn = sum(_to_float(r.get("strict_fn")) or 0 for r in rows)
    tn = sum(_to_float(r.get("strict_tn")) or 0 for r in rows)

    if tp + fp + fn + tn > 0:
        precision = clean_float(tp / (tp + fp)) if tp + fp else 0.0
        recall = clean_float(tp / (tp + fn)) if tp + fn else 0.0
        f1 = clean_float(2 * precision * recall / (precision + recall)) if precision + recall else 0.0
        accuracy = clean_float((tp + tn) / (tp + tn + fp + fn)) if tp + tn + fp + fn else 0.0

        for metric, value in {
            "strict_precision_micro": precision,
            "strict_recall_micro": recall,
            "strict_f1_micro": f1,
            "strict_accuracy_micro": accuracy,
        }.items():
            out.append({
                "metric": metric,
                "documents_total": n,
                "documents_with_value": n,
                "coverage": 1.0 if n else "",
                "mean": value,
                "std": "",
                "min": "",
                "p25": "",
                "median": "",
                "p75": "",
                "p90": "",
                "p95": "",
                "max": "",
            })

    return out


def strict_confusion_matrix_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    n = len(rows)
    totals = {
        "strict_tp_total": sum(_to_float(r.get("strict_tp")) or 0 for r in rows),
        "strict_fp_total": sum(_to_float(r.get("strict_fp")) or 0 for r in rows),
        "strict_fn_total": sum(_to_float(r.get("strict_fn")) or 0 for r in rows),
        "strict_tn_total": sum(_to_float(r.get("strict_tn")) or 0 for r in rows),
    }
    return [{"metric": k, "documents_total": n, "value": clean_float(v)} for k, v in totals.items()]


def fuzzy_content_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    metrics = [m for m in FUZZY_FINAL_METRICS if any(m in row for row in rows)]
    return _continuous_summary(rows, metrics)


def write_split_effectiveness_reports(effectiveness_csv: str | Path, output_dir: str | Path) -> dict[str, Path]:
    """Generate family-specific effectiveness reports from document-level rows."""
    rows = _read_rows(effectiveness_csv)
    output_dir = Path(output_dir)

    files = {
        "structural_results": output_dir / "effectiveness_structural_results.csv",
        "structural_summary": output_dir / "effectiveness_structural_summary.csv",
        "strict_results": output_dir / "effectiveness_strict_content_results.csv",
        "strict_summary": output_dir / "effectiveness_strict_content_summary.csv",
        "strict_confusion": output_dir / "effectiveness_strict_content_confusion_matrix.csv",
        "fuzzy_results": output_dir / "effectiveness_fuzzy_content_results.csv",
        "fuzzy_summary": output_dir / "effectiveness_fuzzy_content_summary.csv",
    }

    _write_rows(_project_rows(rows, STRUCTURAL_DOCUMENT_COLUMNS), files["structural_results"])
    _write_rows(structural_summary(rows), files["structural_summary"])

    _write_rows(_project_rows(rows, STRICT_DOCUMENT_COLUMNS), files["strict_results"])
    _write_rows(strict_content_summary(rows), files["strict_summary"])
    _write_rows(strict_confusion_matrix_summary(rows), files["strict_confusion"])

    _write_rows(_project_rows(rows, FUZZY_DOCUMENT_COLUMNS), files["fuzzy_results"])
    _write_rows(fuzzy_content_summary(rows), files["fuzzy_summary"])

    return files
