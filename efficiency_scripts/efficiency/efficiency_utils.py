from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Set, Tuple

from rdflib import Graph, Literal, RDF, RDFS, OWL, URIRef
from rdflib.term import Node


RDF_PROPERTY_TYPES = {
    RDF.Property,
    OWL.ObjectProperty,
    OWL.DatatypeProperty,
    OWL.AnnotationProperty,
    OWL.FunctionalProperty,
    OWL.InverseFunctionalProperty,
    OWL.TransitiveProperty,
    OWL.SymmetricProperty,
    OWL.AsymmetricProperty,
    OWL.ReflexiveProperty,
    OWL.IrreflexiveProperty,
}

RDF_CLASS_TYPES = {OWL.Class, RDFS.Class}

BUILTIN_NAMESPACES = (
    str(RDF),
    str(RDFS),
    str(OWL),
    "http://www.w3.org/2001/XMLSchema#",
)

Triple = Tuple[Node, Node, Node]
POPair = Tuple[Node, Node]

def build_universe_po(gold_dir: Path, pred_dir: Optional[Path], fmt: str = "turtle") -> set[POPair]:
    universe: set[POPair] = set()
    for path in gold_dir.glob("*.ttl"):
        result = parse_rdf(path, fmt=fmt)
        if result.ok and result.graph is not None:
            universe.update(predicate_object_pairs(result.graph))
    if pred_dir is not None:
        for path in pred_dir.glob("*.ttl"):
            result = parse_rdf(path, fmt=fmt)
            if result.ok and result.graph is not None:
                universe.update(predicate_object_pairs(result.graph))
    return universe

@dataclass(frozen=True)
class ParseResult:
    ok: bool
    graph: Optional[Graph] = None
    error: Optional[str] = None


def parse_rdf(path: str | Path, fmt: str = "turtle") -> ParseResult:
    """Parse RDF and return a structured result instead of raising."""
    g = Graph()
    try:
        g.parse(str(path), format=fmt)
        return ParseResult(ok=True, graph=g)
    except Exception as exc:  # rdflib raises several parser-specific exceptions
        return ParseResult(ok=False, graph=None, error=f"{type(exc).__name__}: {exc}")


def load_rdf(path: str | Path, fmt: str = "turtle") -> Graph:
    """Parse RDF and raise a ValueError with a readable message on failure."""
    result = parse_rdf(path, fmt=fmt)
    if not result.ok or result.graph is None:
        raise ValueError(f"Could not parse RDF file {path}: {result.error}")
    return result.graph

def is_builtin_uri(uri: Node) -> bool:
    return isinstance(uri, URIRef) and str(uri).startswith(BUILTIN_NAMESPACES)


def extract_ontology_classes(ontology: Graph, include_builtin: bool = False) -> Set[URIRef]:
    """Return classes explicitly declared in the ontology.

    The function intentionally relies on explicit declarations. It also includes
    URIRefs appearing as rdfs:domain/rdfs:range values when they are declared as
    classes elsewhere.
    """
    classes: Set[URIRef] = set()
    for class_type in RDF_CLASS_TYPES:
        classes.update(s for s in ontology.subjects(RDF.type, class_type) if isinstance(s, URIRef))
    if not include_builtin:
        classes = {c for c in classes if not is_builtin_uri(c)}
    return classes


def extract_ontology_properties(ontology: Graph, include_builtin: bool = False) -> Set[URIRef]:
    """Return properties explicitly declared in the ontology.

    Includes common RDF/OWL property classes and properties that have declared
    domain or range, because lightweight ontologies sometimes omit rdf:type.
    """
    props: Set[URIRef] = set()
    for prop_type in RDF_PROPERTY_TYPES:
        props.update(s for s in ontology.subjects(RDF.type, prop_type) if isinstance(s, URIRef))
    props.update(s for s in ontology.subjects(RDFS.domain, None) if isinstance(s, URIRef))
    props.update(s for s in ontology.subjects(RDFS.range, None) if isinstance(s, URIRef))
    if not include_builtin:
        props = {p for p in props if not is_builtin_uri(p)}
    return props