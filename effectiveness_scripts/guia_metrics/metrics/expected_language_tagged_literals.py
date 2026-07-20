from __future__ import annotations

from pathlib import Path
from guia_metrics.common import parse_graph, language_tagged_literals, safe_divide


METRIC_NAME = "expected_language_tagged_literals"


def compute(pred_file: str | Path, gold_file: str | Path, ontology_graph=None, logger=None, rdf_format="turtle", **kwargs):
    try:
        pred = parse_graph(pred_file, rdf_format)
        gold = parse_graph(gold_file, rdf_format)
        pred_count = len(language_tagged_literals(pred))
        gold_count = len(language_tagged_literals(gold))
        return {"expected_language_tagged_literals": safe_divide(pred_count, gold_count),
                "language_tagged_literals_pred": pred_count, "language_tagged_literals_gold": gold_count}
    except Exception as e:
        if logger:
            logger.log(METRIC_NAME, "Expected language-tagged literals metric failed.",
                       pred_file=str(pred_file), gold_file=str(gold_file), exception=e)
        return {"expected_language_tagged_literals": None, "language_tagged_literals_pred": None, "language_tagged_literals_gold": None}
