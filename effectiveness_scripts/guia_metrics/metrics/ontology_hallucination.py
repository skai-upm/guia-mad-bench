from __future__ import annotations

from pathlib import Path
from rdflib import RDF
from guia_metrics.common import parse_graph, load_ontology_classes, load_ontology_properties, default_allowed_predicates


METRIC_NAME = "ontology_hallucination"


def compute(pred_file: str | Path, gold_file=None, ontology_graph=None, shapes_file=None, logger=None, rdf_format="turtle", **kwargs):
    if ontology_graph is None:
        if logger:
            logger.log(METRIC_NAME, "Ontology graph not provided. Hallucination values left empty.",
                       pred_file=str(pred_file), gold_file=str(gold_file) if gold_file else None)
        return {"class_hallucination": None, "property_hallucination": None,
                "hallucinated_classes": "", "hallucinated_properties": ""}
    try:
        pred = parse_graph(pred_file, rdf_format)
        ontology_classes = load_ontology_classes(ontology_graph)
        ontology_properties = load_ontology_properties(ontology_graph) | default_allowed_predicates()
        used_classes = {o for _, _, o in pred.triples((None, RDF.type, None))}
        used_properties = {p for _, p, _ in pred.triples((None, None, None))}
        hallucinated_classes = sorted(str(c) for c in (used_classes - ontology_classes))
        hallucinated_properties = sorted(str(p) for p in (used_properties - ontology_properties))
        return {
            "class_hallucination": len(hallucinated_classes),
            "property_hallucination": len(hallucinated_properties),
            "hallucinated_classes": hallucinated_classes,
            "hallucinated_properties": hallucinated_properties,
        }
    except Exception as e:
        if logger:
            logger.log(METRIC_NAME, "Ontology hallucination metric failed.",
                       pred_file=str(pred_file), gold_file=str(gold_file) if gold_file else None, exception=e)
        return {"class_hallucination": None, "property_hallucination": None,
                "hallucinated_classes": "", "hallucinated_properties": ""}
