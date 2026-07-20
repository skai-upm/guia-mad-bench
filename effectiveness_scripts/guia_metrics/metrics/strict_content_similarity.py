from __future__ import annotations

from pathlib import Path
from guia_metrics.common import parse_graph, predicate_object_pairs, safe_divide


METRIC_NAME = "strict_content_similarity"


def compute(pred_file: str | Path, gold_file: str | Path, ontology_graph=None, logger=None, rdf_format="turtle", universe_file=None, **kwargs):
    try:
        pred = parse_graph(pred_file, rdf_format)
        gold = parse_graph(gold_file, rdf_format)
        po_pred = predicate_object_pairs(pred)
        po_gold = predicate_object_pairs(gold)
        tp = len(po_pred & po_gold)
        fp = len(po_pred - po_gold)
        fn = len(po_gold - po_pred)

        # The paper defines TN with respect to a universe of predicate-object pairs.
        # If no explicit universe is provided, we cannot infer true negatives safely.
        # Therefore, we use TN=0 and log this decision.
        tn = 0
        if universe_file and Path(universe_file).exists():
            universe = set()
            with open(universe_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        universe.add(line)
            observed = {f"{p} {o}" for p, o in (po_pred | po_gold)}
            tn = len(universe - observed)
        elif logger:
            logger.log(METRIC_NAME, "No predicate-object universe was provided. TN set to 0 for accuracy computation.",
                       pred_file=str(pred_file), gold_file=str(gold_file))

        precision = safe_divide(tp, tp + fp, 0.0)
        recall = safe_divide(tp, tp + fn, 0.0)
        f1 = safe_divide(2 * precision * recall, precision + recall, 0.0) if precision is not None and recall is not None else None
        accuracy = safe_divide(tp + tn, tp + tn + fp + fn, 0.0)
        return {
            "strict_tp": tp, "strict_fp": fp, "strict_fn": fn, "strict_tn": tn,
            "strict_precision": precision, "strict_recall": recall,
            "strict_f1": f1, "strict_accuracy": accuracy,
        }
    except Exception as e:
        if logger:
            logger.log(METRIC_NAME, "Strict content similarity metric failed.",
                       pred_file=str(pred_file), gold_file=str(gold_file), exception=e)
        return {"strict_tp": None, "strict_fp": None, "strict_fn": None, "strict_tn": None,
                "strict_precision": None, "strict_recall": None, "strict_f1": None, "strict_accuracy": None}
