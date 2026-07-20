from __future__ import annotations

from pathlib import Path
from guia_metrics.common import parse_graph, datatype_literals, safe_divide


METRIC_NAME = "expected_datatype_literals"


def compute(pred_file: str | Path, gold_file: str | Path, ontology_graph=None, logger=None, rdf_format="turtle", **kwargs):
    try:
        pred = parse_graph(pred_file, rdf_format)
        gold = parse_graph(gold_file, rdf_format)
        pred_count = len(datatype_literals(pred))
        gold_count = len(datatype_literals(gold))
        return {"expected_datatype_literals": safe_divide(pred_count, gold_count),
                "datatype_literals_pred": pred_count, "datatype_literals_gold": gold_count}
    except Exception as e:
        if logger:
            logger.log(METRIC_NAME, "Expected datatype literals metric failed.",
                       pred_file=str(pred_file), gold_file=str(gold_file), exception=e)
        return {"expected_datatype_literals": None, "datatype_literals_pred": None, "datatype_literals_gold": None}
