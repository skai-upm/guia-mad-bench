import os
import time
from pathlib import Path
import numpy as np
import pandas as pd
from rdflib import Graph
from guia_metrics.rdf_utils import load_rdf, extract_ontology_classes, extract_ontology_properties
from guia_metrics.evaluate import build_universe_po

try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    SentenceTransformer = None

# Parámetros oficiales definidos en el artículo
ALPHA_UTILITY = 1.0  # Beneficio por tripleta correcta
BETA_UTILITY = 2.0  # Penalización por tripleta incorrecta (debe ser > ALPHA)
TAU_TARGET_THRESHOLD = 0.80  # Umbral tau para Time-to-Target (F1 o Similitud)

def graph_to_po_tuples(graph: Graph) -> set[tuple[str, str]]:
    return {(str(p).strip(), str(o).strip()) for s, p, o in graph}

def calculate_lexical_overlap(pred_set: set, gold_set: set) -> tuple[int, int, int]:
    tp = len(pred_set.intersection(gold_set))
    fp = len(pred_set - gold_set)
    fn = len(gold_set - pred_set)
    return tp, fp, fn

def calculate_semantic_similarity(pred_set: set, gold_set: set, model) -> float:
    if not model or not pred_set or not gold_set:
        return 0.0
    pred_list = [f"{p} {o}" for p, o in pred_set]
    gold_list = [f"{p} {o}" for p, o in gold_set]
    pred_embeddings = model.encode(pred_list, convert_to_tensor=True)
    gold_embeddings = model.encode(gold_list, convert_to_tensor=True)
    cosine_scores = util.cos_sim(pred_embeddings, gold_embeddings)
    max_scores, _ = cosine_scores.max(dim=1)
    return float(max_scores.mean())

def compute_vtps(tp: int, total_time: float) -> float:
    if total_time <= 0: return 0.0
    return tp / total_time

def compute_nur(tp: int, fp: int, total_time: float, alpha: float = ALPHA_UTILITY, beta: float = BETA_UTILITY) -> float:
    if total_time <= 0: return 0.0
    net_utility = (tp * alpha) - (fp * beta)
    return net_utility / total_time

def compute_semspeed(semantic_similarity: float, total_time: float) -> float:
    if total_time <= 0 or np.isnan(semantic_similarity): return 0.0
    return semantic_similarity / np.log10(total_time + 1)

def compute_ttt(f1: float, total_time: float, tau: float = TAU_TARGET_THRESHOLD) -> float:
    return total_time if f1 >= tau else float('inf')

def evaluate_benchmark(
        pred_dir: str | Path,
        gold_dir: str | Path,
        monitor_data: str | Path,
        ontology_path: str | Path,
        shapes_path: str | Path | None = None,
        output_results_csv: str | Path = "correctness_results.csv",
        output_agg_csv: str | Path = "correctness_agg_results.csv",
        fmt: str = "turtle",
        compute_semantic: bool = False,
        semantic_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        include_predictions_in_universe: bool = True,  # <--- NUEVO: Recibe el tiempo real del monitor
) -> tuple[pd.DataFrame, pd.DataFrame]:
    
    pred_dir = Path(pred_dir)
    gold_dir = Path(gold_dir)

    s_model = None
    if compute_semantic and SentenceTransformer:
        print(f"Loading semantic model: {semantic_model}...")
        s_model = SentenceTransformer(semantic_model)

    detailed_results = []
    ext_map = {"turtle": "ttl", "xml": "rdf", "ntriples": "nt", "n3": "n3"}
    ext_real = ext_map.get(fmt.lower(), fmt)
    gold_files = list(gold_dir.glob(f"*.{ext_real}"))

    if not gold_files:
        print(f"[Error] No se encontraron archivos de referencia en {gold_dir}")
        return pd.DataFrame(), pd.DataFrame()

    total_generation_time = None
    if monitor_data:
        monitor_path = Path(monitor_data)
        if monitor_path.exists():
            try:
                df_mon = pd.read_csv(monitor_path)
                if "Total_Seconds" in df_mon.columns:
                    total_generation_time = float(df_mon["Total_Seconds"].iloc[0])
            except Exception as e:
                print(f"[Aviso] Error leyendo Total_Seconds de {monitor_path}: {e}")

    num_docs = len(gold_files)
    avg_doc_time = (total_generation_time / num_docs) if total_generation_time else None

    for g_file in gold_files:
        start_time = time.perf_counter()
        
        gold_graph = load_rdf(g_file, fmt=fmt)
        pred_graph = Graph()
        if (pred_dir / g_file.name).exists():
            try:
                pred_graph = load_rdf(pred_dir / g_file.name, fmt=fmt)
            except Exception:
                pass # Fallback simplificado por legibilidad

        gold_set = graph_to_po_tuples(gold_graph)
        pred_set = graph_to_po_tuples(pred_graph)

        tp, fp, fn = calculate_lexical_overlap(pred_set, gold_set)
        total_generated = len(pred_set)

        precision = tp / total_generated if total_generated > 0 else 0.0
        recall = tp / len(gold_set) if len(gold_set) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        end_time = time.perf_counter()
        
        if avg_doc_time is not None:
            doc_duration = avg_doc_time
        else:
            doc_duration = max(end_time - start_time, 0.001)

        sem_sim = calculate_semantic_similarity(pred_set, gold_set, s_model) if compute_semantic else np.nan

        vtps = compute_vtps(tp, doc_duration)
        nur = compute_nur(tp, fp, doc_duration)
        sem_speed = compute_semspeed(sem_sim, doc_duration)
        ttt = compute_ttt(f1, doc_duration)

        detailed_results.append({
            "document": g_file.stem,
            "tp": tp, "fp": fp, "fn": fn,
            "precision": precision, "recall": recall, "f1_score": f1,
            "semantic_similarity": sem_sim,
            "duration_seconds": doc_duration,
            "VTPS": vtps,
            "NUR": nur,
            "SemSpeed": sem_speed,
            "TTT": ttt
        })

    df_results = pd.DataFrame(detailed_results)

    total_tp = df_results["tp"].sum()
    total_fp = df_results["fp"].sum()
    total_fn = df_results["fn"].sum()
    avg_sem_sim = df_results["semantic_similarity"].mean()

    micro_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    micro_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_denominator = (2 * total_tp) + total_fp + total_fn
    micro_f1 = (2 * total_tp) / micro_denominator if micro_denominator > 0 else 0.0

   
    if total_generation_time is not None:
        total_duration = total_generation_time
    else:
        total_duration = df_results["duration_seconds"].sum()

    agg_summary = {
        "total_documents": [len(df_results)],
        "micro_precision": [micro_precision],
        "micro_recall": [micro_recall],
        "micro_f1_score": [micro_f1],
        "total_duration_seconds": [total_duration],
        "VTPS_global": [compute_vtps(total_tp, total_duration)],
        "NUR_global": [compute_nur(total_tp, total_fp, total_duration)],
        "SemSpeed_global": [compute_semspeed(avg_sem_sim, total_duration)],
        "TTT_global": [compute_ttt(micro_f1, total_duration)]
    }

    df_agg = pd.DataFrame(agg_summary)
    df_results.to_csv(output_results_csv, index=False)
    df_agg.to_csv(output_agg_csv, index=False)

    return df_results, df_agg