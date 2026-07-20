#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import importlib
from pathlib import Path
from typing import Any

from guia_metrics.common import parse_graph, as_csv_value
from guia_metrics.logger import ExtendedReportLogger
from guia_metrics.aggregation.split_reports import write_split_effectiveness_reports


METRICS = {
    "syntactic_consistency": "guia_metrics.metrics.syntactic_consistency",
    "ontology_conformance": "guia_metrics.metrics.ontology_conformance",
    "ontology_hallucination": "guia_metrics.metrics.ontology_hallucination",
    "expected_typed_instances": "guia_metrics.metrics.expected_typed_instances",
    "expected_properties": "guia_metrics.metrics.expected_properties",
    "expected_datatype_literals": "guia_metrics.metrics.expected_datatype_literals",
    "expected_language_tagged_literals": "guia_metrics.metrics.expected_language_tagged_literals",
    "strict_content_similarity": "guia_metrics.metrics.strict_content_similarity",
    "lexical_content_similarity": "guia_metrics.metrics.lexical_content_similarity",
    "semantic_content_similarity": "guia_metrics.metrics.semantic_content_similarity",
}

DEFAULT_METRICS = [
    "syntactic_consistency",
    "ontology_conformance",
    "ontology_hallucination",
    "expected_typed_instances",
    "expected_properties",
    "expected_datatype_literals",
    "expected_language_tagged_literals",
    "strict_content_similarity",
    "lexical_content_similarity",
    "semantic_content_similarity",
]


def load_metric(name: str):
    if name not in METRICS:
        raise ValueError(f"Unknown metric '{name}'. Available metrics: {', '.join(METRICS)}")
    return importlib.import_module(METRICS[name])


def load_ontology(path: str | None, logger: ExtendedReportLogger | None):
    if not path:
        return None
    try:
        return parse_graph(path)
    except Exception as exc:
        if logger:
            logger.log("load_ontology", "Could not parse ontology file.", exception=exc)
        return None


def find_pairs(pred_dir: Path, gold_dir: Path) -> list[tuple[Path, Path]]:
    """Find prediction/gold pairs by filename stem.

    Example:
      predictions/course-guide-7198012.ttl
      gold/course-guide-7198012.ttl
    """
    gold_by_stem = {gold.stem: gold for gold in gold_dir.rglob("*.ttl")}
    pairs = []
    for pred in pred_dir.rglob("*.ttl"):
        gold = gold_by_stem.get(pred.stem)
        if gold:
            pairs.append((pred, gold))
    return sorted(pairs, key=lambda pair: pair[0].name)


def write_rows(rows: list[dict[str, Any]], output_csv: Path):
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    with output_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: as_csv_value(row.get(key, "")) for key in fieldnames})


def compute_metrics_for_pair(
    pred_file: Path,
    gold_file: Path,
    metrics: list[str],
    args,
    logger: ExtendedReportLogger,
):
    ontology_graph = getattr(args, "_ontology_graph", None)
    if ontology_graph is None and args.ontology:
        ontology_graph = load_ontology(args.ontology, logger)

    result = {
        "file": pred_file.name,
        "pred_file": str(pred_file),
        "gold_file": str(gold_file),
    }

    for metric_name in metrics:
        metric_module = load_metric(metric_name)
        metric_result = metric_module.compute(
            pred_file=pred_file,
            gold_file=gold_file,
            ontology_graph=ontology_graph,
            shapes_file=args.shapes,
            logger=logger,
            rdf_format=args.rdf_format,
            universe_file=getattr(args, "universe_file", None),
            semantic_methods=getattr(args, "semantic_methods", "sentence_bert,bertscore"),
            sentence_model=getattr(args, "sentence_model", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"),
            bertscore_lang=getattr(args, "bertscore_lang", "es"),
            semantic_batch_size=getattr(args, "semantic_batch_size", 32),
            semantic_max_pairs_per_property=getattr(args, "semantic_max_pairs_per_property", 0),
        )
        result.update(metric_result)

    return result


def cmd_effectiveness_report(args):
    output_dir = Path(args.output_dir)
    logger = ExtendedReportLogger(output_dir / "extended-report.txt")
    metrics = DEFAULT_METRICS if args.metrics == ["all"] else args.metrics

    args._ontology_graph = load_ontology(args.ontology, logger) if args.ontology else None
    pairs = find_pairs(Path(args.pred_dir), Path(args.gold_dir))

    if not pairs:
        logger.log("effectiveness_report", "No matching predicted/gold Turtle file pairs were found.")
        raise SystemExit("No matching predicted/gold Turtle file pairs were found.")

    rows = [
        compute_metrics_for_pair(pred_file, gold_file, metrics, args, logger)
        for pred_file, gold_file in pairs
    ]

    # Internal document-level file used to build the split reports. It is kept
    # because it is useful for debugging, but it is not a legacy aggregate.
    effectiveness_csv = output_dir / "effectiveness_results.csv"
    write_rows(rows, effectiveness_csv)

    split_files = write_split_effectiveness_reports(effectiveness_csv, output_dir)

    print(f"Wrote {effectiveness_csv}")
    for split_file in split_files.values():
        print(f"Wrote {split_file}")
    print(f"Wrote {output_dir / 'extended-report.txt'}")


def cmd_effectiveness_metric(args):
    output_dir = Path(args.output_dir)
    logger = ExtendedReportLogger(output_dir / "extended-report.txt")
    row = compute_metrics_for_pair(
        Path(args.pred_file),
        Path(args.gold_file),
        [args.metric_name],
        args,
        logger,
    )
    output_csv = output_dir / f"{args.metric_name}_results.csv"
    write_rows([row], output_csv)
    print(f"Wrote {output_csv}")
    print(f"Wrote {output_dir / 'extended-report.txt'}")


def build_parser():
    parser = argparse.ArgumentParser(description="GUIA-Madrid-Bench effectiveness metric CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    eff = sub.add_parser("effectiveness", help="Effectiveness metrics")
    eff_sub = eff.add_subparsers(dest="effectiveness_command", required=True)

    report = eff_sub.add_parser("report", help="Compute effectiveness reports for matching predicted/gold RDF files")
    report.add_argument("--pred-dir", required=True, help="Directory with predicted Turtle files.")
    report.add_argument("--gold-dir", required=True, help="Directory with gold-standard Turtle files.")
    report.add_argument("--ontology", help="GUIA ontology Turtle file.")
    report.add_argument("--shapes", help="SHACL shapes Turtle file.")
    report.add_argument("--output-dir", required=True, help="Directory where reports will be written.")
    report.add_argument("--rdf-format", default="turtle")
    report.add_argument("--metrics", nargs="+", default=["all"], help="Metric names or 'all'.")
    report.add_argument("--universe-file", help="Optional universe of predicate-object pairs for strict accuracy.")
    report.add_argument(
        "--semantic-methods",
        default="sentence_bert,bertscore",
        help="Comma-separated semantic methods: sentence_bert,bertscore. Use 'none' to skip semantic metrics.",
    )
    report.add_argument(
        "--sentence-model",
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        help="SentenceTransformer model used by sentence_bert.",
    )
    report.add_argument("--bertscore-lang", default="es", help="Language used by BERTScore.")
    report.add_argument("--semantic-batch-size", type=int, default=32)
    report.add_argument(
        "--semantic-max-pairs-per-property",
        type=int,
        default=0,
        help="0 means exact all-vs-all literal comparison. Positive values cap comparisons per property.",
    )
    report.set_defaults(func=cmd_effectiveness_report)

    metric = eff_sub.add_parser("metric", help="Compute one metric for one predicted/gold RDF pair")
    metric.add_argument("metric_name", choices=list(METRICS.keys()))
    metric.add_argument("--pred-file", required=True)
    metric.add_argument("--gold-file", required=True)
    metric.add_argument("--ontology")
    metric.add_argument("--shapes")
    metric.add_argument("--output-dir", required=True)
    metric.add_argument("--rdf-format", default="turtle")
    metric.add_argument("--universe-file")
    metric.add_argument("--semantic-methods", default="sentence_bert,bertscore")
    metric.add_argument("--sentence-model", default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    metric.add_argument("--bertscore-lang", default="es")
    metric.add_argument("--semantic-batch-size", type=int, default=32)
    metric.add_argument("--semantic-max-pairs-per-property", type=int, default=0)
    metric.set_defaults(func=cmd_effectiveness_metric)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
