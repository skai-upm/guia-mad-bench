from __future__ import annotations

from pathlib import Path
from guia_metrics.common import parse_graph


METRIC_NAME = "ontology_conformance"


def compute(pred_file: str | Path, gold_file=None, ontology_graph=None, shapes_file=None, logger=None, rdf_format="turtle", **kwargs):
    if shapes_file is None:
        if logger:
            logger.log(METRIC_NAME, "No SHACL shapes file was provided. CSV value set to false.",
                       pred_file=str(pred_file), gold_file=str(gold_file) if gold_file else None)
        return {"ontology_conformance": False}
    try:
        from pyshacl import validate
    except Exception as e:
        if logger:
            logger.log(METRIC_NAME, "pyshacl is not installed or cannot be imported. CSV value set to false.",
                       pred_file=str(pred_file), gold_file=str(gold_file) if gold_file else None, exception=e)
        return {"ontology_conformance": False}
    try:
        data_graph = parse_graph(pred_file, rdf_format)
        conforms, results_graph, results_text = validate(data_graph=data_graph, shacl_graph=str(shapes_file), inference="rdfs")
        if not conforms and logger:
            logger.log(METRIC_NAME, "SHACL validation failed. CSV value set to false.\n" + str(results_text),
                       pred_file=str(pred_file), gold_file=str(gold_file) if gold_file else None)
        return {"ontology_conformance": bool(conforms)}
    except Exception as e:
        if logger:
            logger.log(METRIC_NAME, "SHACL validation raised an exception. CSV value set to false.",
                       pred_file=str(pred_file), gold_file=str(gold_file) if gold_file else None, exception=e)
        return {"ontology_conformance": False}
