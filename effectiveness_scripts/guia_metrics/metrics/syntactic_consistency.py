from __future__ import annotations

from pathlib import Path
from guia_metrics.common import parse_graph, find_invalid_xsd_literals


METRIC_NAME = "syntactic_consistency"


def compute(pred_file: str | Path, gold_file=None, ontology_graph=None, shapes_file=None, logger=None, rdf_format="turtle", **kwargs):
    """Check whether the predicted RDF file can be parsed as valid RDF/Turtle.

    This implements the Syntactic consistency metric described in the current
    GUIA-Madrid-Bench article. It replaces the former name
    `lexical_consistency`, while keeping the same operational definition:
    parsing succeeds => true; parsing fails => false.
    """
    try:
        graph = parse_graph(pred_file, rdf_format)
        invalid_literals = find_invalid_xsd_literals(graph)
        if logger:
            logger.log(METRIC_NAME, "RDF parsing succeeded.", pred_file=str(pred_file), gold_file=str(gold_file) if gold_file else None)
            if invalid_literals:
                details = "\n".join(
                    f"- subject={item['subject']} | predicate={item['predicate']} | literal={item['literal']} | datatype={item['datatype']}"
                    for item in invalid_literals
                )
                logger.log(
                    METRIC_NAME,
                    "The file is valid Turtle, but some typed literals have invalid lexical forms for their declared XSD datatype. "
                    "The CSV syntactic_consistency value remains true because the metric checks RDF/Turtle parsing; "
                    "datatype-quality issues should be inspected here and, when applicable, by SHACL validation.\n" + details,
                    pred_file=str(pred_file),
                    gold_file=str(gold_file) if gold_file else None,
                )
        return {"syntactic_consistency": True}
    except Exception as e:
        if logger:
            logger.log(METRIC_NAME, "RDF parsing failed. CSV value set to false.", pred_file=str(pred_file),
                       gold_file=str(gold_file) if gold_file else None, exception=e)
        return {"syntactic_consistency": False}
