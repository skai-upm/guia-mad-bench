#!/usr/bin/env python3
"""Runner for GUIA-MAD-BENCH Efficiency Metrics.

This script evaluates only the computational and correctness efficiency of a
proposal, skipping the heavy effectiveness semantic metrics unless strictly required.

It calculates:
1. Generation Efficiency (DPR, TpS, ADL)
2. Correctness Efficiency (VTPS, NUR, SemSpeed, TTT)
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable
import pandas as pd

from efficiency.generation import evaluate_efficiency
from efficiency.correctness_efficiency import evaluate_benchmark as evaluate_correctness


def _check_efficiency_inputs(pred_dir: Path, gold_dir: Path, monitor_csv: Path) -> None:
    errors: list[str] = []
    if not pred_dir.exists() or not pred_dir.is_dir():
        errors.append(f"Prediction directory does not exist: {pred_dir}")
    if not gold_dir.exists() or not gold_dir.is_dir():
        errors.append(f"Gold directory does not exist: {gold_dir}")
    if not monitor_csv.exists() or not monitor_csv.is_file():
        errors.append(f"Monitor CSV file missing (run monitor.py first): {monitor_csv}")
    if errors:
        raise SystemExit("\n".join(errors))


def print_efficiency_summary(gen_df: pd.DataFrame, corr_agg_df: pd.DataFrame) -> None:
    print("\nGUIA-MAD-BENCH Efficiency Summary")
    print("=" * 56)

    # Generation metrics
    if not gen_df.empty:
        row = gen_df.iloc[0]
        print("Generation Efficiency (Computational)")
        print(f"  Total Docs Generated:      {row.get('N_documents', 'N/A')}")
        print(f"  Total Triples Generated:   {row.get('N_RDF', 'N/A')}")
        print(f"  Total Time (seconds):      {row.get('T_seconds', 'N/A')}")
        print(f"  DPR (Docs/min):            {row.get('DPR', 'N/A')}")
        print(f"  TpS (Triples/sec):         {row.get('TpS', 'N/A')}")
        print(f"  ADL (Sec/Doc):             {row.get('ADL', 'N/A')}")
    else:
        print("[Warning] Generation Efficiency data is empty.")

    print("")

    # Correctness metrics
    if not corr_agg_df.empty:
        row = corr_agg_df.iloc[0]
        print("Correctness Efficiency (Productivity)")
        print(f"  Micro F1 Score:            {row.get('micro_f1_score', 0):.4f}")
        print(f"  VTPS (Valid Triples/sec):  {row.get('VTPS_global', 0):.4f}")
        print(f"  NUR (Net Utility Rate):    {row.get('NUR_global', 0):.4f}")
        print(f"  SemSpeed (Semantic/sec):   {row.get('SemSpeed_global', 0):.4f}")

        ttt = row.get('TTT_global', float('inf'))
        ttt_str = f"{ttt:.4f} seconds" if ttt != float('inf') else "Did not converge (inf)"
        print(f"  TTT (Time-to-Target):      {ttt_str}")
    else:
        print("[Warning] Correctness Efficiency data is empty.")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run GUIA-MAD-BENCH Efficiency metrics.")
    parser.add_argument("--pred-dir", required=True, help="Directory containing predicted .ttl files.")
    parser.add_argument("--gold-dir", required=True, help="Directory containing gold-standard .ttl files.")
    parser.add_argument("--ontology", required=True, help="GUIA ontology Turtle file.")
    parser.add_argument("--shapes", default=None, help="Optional GUIA SHACL shapes Turtle file.")
    parser.add_argument("--output-dir", default=".", help="Directory where CSV results will be written.")
    parser.add_argument("--format", default="turtle", help="RDF serialization format. Default: turtle.")
    parser.add_argument("--semantic", action="store_true", help="Enable transformer-based semantic lexical similarity.")
    parser.add_argument("--semantic-model", default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    parser.add_argument("--quiet", action="store_true", help="Do not print summary to stdout.")

    args = parser.parse_args(list(argv) if argv is not None else None)

    pred_dir = Path(args.pred_dir)
    gold_dir = Path(args.gold_dir)
    output_dir = Path(args.output_dir)
    ontology = Path(args.ontology)
    shapes = Path(args.shapes) if args.shapes else None
    monitor_summary_csv = output_dir / "monitor_results_summary.csv"

    output_dir.mkdir(parents=True, exist_ok=True)
    _check_efficiency_inputs(pred_dir, gold_dir, monitor_summary_csv)

    efficiency_csv = output_dir / "efficiency_results.csv"
    correctness_results_csv = output_dir / "correctness_results.csv"
    correctness_agg_csv = output_dir / "correctness_agg_results.csv"

    # 1. Generation Efficiency
    gen_df = evaluate_efficiency(
        pred_dir=pred_dir,
        monitor_summary_csv=monitor_summary_csv,
        output_results_csv=efficiency_csv,
        fmt=args.format
    )

    # 2. Correctness Efficiency
    corr_df, corr_agg_df = evaluate_correctness(
        pred_dir=pred_dir,
        gold_dir=gold_dir,
        ontology_path=ontology,
        shapes_path=shapes,
        output_results_csv=correctness_results_csv,
        output_agg_csv=correctness_agg_csv,
        fmt=args.format,
        compute_semantic=args.semantic,
        semantic_model=args.semantic_model,
        include_predictions_in_universe=True, 
        monitor_data=monitor_summary_csv# Por defecto True en este contexto
    )

    if not args.quiet:
        print_efficiency_summary(gen_df, corr_agg_df)
        print("\nEfficiency files successfully generated in:", str(output_dir))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())