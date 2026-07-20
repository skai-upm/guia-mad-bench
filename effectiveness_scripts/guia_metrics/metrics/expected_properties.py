from __future__ import annotations

from pathlib import Path
from guia_metrics.common import parse_graph, load_ontology_properties, property_assertion_triples, safe_divide


METRIC_NAME = "expected_properties"


def compute(pred_file: str | Path, gold_file: str | Path, ontology_graph=None, logger=None, rdf_format="turtle", **kwargs):
    try:
        pred = parse_graph(pred_file, rdf_format)
        gold = parse_graph(gold_file, rdf_format)
        props = load_ontology_properties(ontology_graph) if ontology_graph is not None else {p for _, p, _ in gold.triples((None, None, None))}
        pred_count = len(property_assertion_triples(pred, props))
        gold_count = len(property_assertion_triples(gold, props))
        return {"expected_properties": safe_divide(pred_count, gold_count),
                "properties_pred": pred_count, "properties_gold": gold_count}
    except Exception as e:
        if logger:
            logger.log(METRIC_NAME, "Expected properties metric failed.",
                       pred_file=str(pred_file), gold_file=str(gold_file), exception=e)
        return {"expected_properties": None, "properties_pred": None, "properties_gold": None}
