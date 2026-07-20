from __future__ import annotations

from pathlib import Path
from guia_metrics.common import parse_graph, load_ontology_classes, typed_instance_triples, safe_divide


METRIC_NAME = "expected_typed_instances"


def compute(pred_file: str | Path, gold_file: str | Path, ontology_graph=None, logger=None, rdf_format="turtle", **kwargs):
    try:
        pred = parse_graph(pred_file, rdf_format)
        gold = parse_graph(gold_file, rdf_format)
        classes = load_ontology_classes(ontology_graph) if ontology_graph is not None else {o for _, _, o in gold.triples((None, None, None))}
        pred_count = len(typed_instance_triples(pred, classes))
        gold_count = len(typed_instance_triples(gold, classes))
        return {"expected_typed_instances": safe_divide(pred_count, gold_count),
                "typed_instances_pred": pred_count, "typed_instances_gold": gold_count}
    except Exception as e:
        if logger:
            logger.log(METRIC_NAME, "Expected typed instances metric failed.",
                       pred_file=str(pred_file), gold_file=str(gold_file), exception=e)
        return {"expected_typed_instances": None, "typed_instances_pred": None, "typed_instances_gold": None}
