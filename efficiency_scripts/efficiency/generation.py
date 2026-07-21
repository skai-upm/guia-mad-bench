import os
import pandas as pd
from pathlib import Path
from rdflib import Graph

import re
from rdflib import Graph
from pathlib import Path


def robust_load_rdf(file_path: Path, fmt: str = "turtle") -> Graph:
    """
    Intenta cargar un archivo RDF. Si falla por errores de sintaxis típicos de LLMs,
    aplica un pre-procesado de limpieza para salvar las tripletas válidas y reintenta.
    """
    g = Graph()

    # Intento 1: Parseo normal (estricto)
    try:
        g.parse(source=str(file_path), format=fmt)
        return g
    except Exception as e:
        # Si falla, no nos rendimos. Pasamos al plan B: Sanitización.
        pass

    # Intento 2: Parseo tras sanitización
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Limpiar bloques de código Markdown (```turtle ... ```)
        content = re.sub(r'```turtle\n?', '', content, flags=re.IGNORECASE)
        content = re.sub(r'```\n?', '', content)

        # 2. Eliminar negritas y cursivas de Markdown (ej: **owl:Object** -> owl:Object)
        content = content.replace('**', '')
        # Arreglo específico para el error que mostraste (*owl:Object*)
        content = re.sub(r'\*(owl:[a-zA-Z]+)\*', r'\1', content)

        # 3. Arreglar comas que deberían ser puntos y comas.
        # Los LLMs a veces ponen ",\n rdfs:label" en lugar de ";\n rdfs:label"
        # Buscamos una coma, seguida de espacios/saltos de línea, seguida de un prefijo común.
        content = re.sub(r',\s*(rdfs:|rdf:|owl:|schema:|:)', r'; \1', content)

        # 4. Eliminar líneas que parecen comentarios inyectados por el LLM en medio del código
        # ej: "Aquí tienes el código:"
        lines = content.split('\n')
        clean_lines = [line for line in lines if not re.match(r'^[A-ZÁÉÍÓÚ]', line) or line.startswith('@')]
        content = '\n'.join(clean_lines)

        # Intentamos parsear el string limpio
        g.parse(data=content, format=fmt)
        return g

    except Exception as fallback_error:
        # Si incluso después de limpiarlo está demasiado roto, devolvemos un grafo vacío.
        # print(f"[Aviso] Imposible salvar el archivo {file_path.name}: {fallback_error}")
        return Graph()


def compute_dpr(n_documents: int, t_minutes: float) -> float:
    """
    Calcula el Documents Processing Rate (DPR).
    Fórmula: N_documents / T_minutes
    """
    if t_minutes <= 0: return 0.0
    return n_documents / t_minutes


def compute_tps(n_rdf: int, t_seconds: float) -> float:
    """
    Calcula Triples per Second (TpS).
    Fórmula: N_RDF / T_seconds
    """
    if t_seconds <= 0: return 0.0
    return n_rdf / t_seconds


def compute_adl(t_seconds: float, n_documents: int) -> float:
    """
    Calcula el Average Document Latency (ADL).
    Fórmula: T_seconds / N_documents
    """
    if n_documents <= 0: return 0.0
    return t_seconds / n_documents


def evaluate_efficiency(
        pred_dir: str | Path,
        monitor_summary_csv: str | Path = "monitor_results_summary.csv",
        output_results_csv: str | Path = "efficiency_results.csv",
        fmt: str = "turtle",
) -> pd.DataFrame:
    """
    Calcula las métricas de eficiencia de generación (DPR, TpS, ADL) basándose
    exclusivamente en el volumen de datos generados y el tiempo invertido.
    """
    pred_dir = Path(pred_dir)
    monitor_summary_csv = Path(monitor_summary_csv)
    output_results_csv = Path(output_results_csv)

    # --- 1. EXTRACCIÓN DE TIEMPO DEL SCRIPT DE MONITORIZACIÓN ---
    t_seconds = 0.0
    if monitor_summary_csv.exists():
        try:
            df_monitor = pd.read_csv(monitor_summary_csv)
            # Aseguramos compatibilidad buscando nombres comunes para la columna de tiempo
            time_col = next((col for col in df_monitor.columns if "second" in col.lower() or "segundo" in col.lower()),
                            None)

            if time_col and not df_monitor.empty:
                t_seconds = float(df_monitor[time_col].iloc[0])
            else:
                print(f"[Aviso] No se encontró la columna de tiempo en {monitor_summary_csv}")
        except Exception as e:
            print(f"[Error] No se pudo leer el CSV del monitor: {e}")
    else:
        print(
            f"[Error] No se encontró el archivo {monitor_summary_csv}. Es obligatorio ejecutar monitor.py previamente.")
        return pd.DataFrame()

    t_minutes = t_seconds / 60.0

    # --- 2. BÚSQUEDA DE DOCUMENTOS Y CONTEO DE TRIPLETAS ---
    n_rdf = 0
    n_documents = 0

    ext_map = {"turtle": "ttl", "xml": "rdf", "ntriples": "nt", "n3": "n3"}
    ext_real = ext_map.get(fmt.lower(), fmt)

    if pred_dir.exists():
        archivos_ttl = list(pred_dir.glob(f"*.{ext_real}"))
        n_documents = len(archivos_ttl)
        print(f"[Info] Analizando {n_documents} documentos generados...")

        for archivo in archivos_ttl:
            # Usamos nuestra nueva función salvavidas
            g = robust_load_rdf(archivo, fmt)
            n_rdf += len(g)
    else:
        print(f"[Error] El directorio de predicciones {pred_dir} no existe.")

    # Comprobación de seguridad
    if t_seconds == 0 or n_documents == 0:
        print("[Error] Faltan datos base (tiempo 0 o sin documentos). Devolviendo DataFrame vacío.")
        return pd.DataFrame()

    # --- 3. CÁLCULO DE MÉTRICAS (Fórmulas del artículo) ---
    dpr = compute_dpr(n_documents, t_minutes)
    tps = compute_tps(n_rdf, t_seconds)
    adl = compute_adl(t_seconds, n_documents)

    # --- 4. EMPAQUETADO Y EXPORTACIÓN ---
    resultados_dict = {
        "N_documents": [n_documents],
        "N_RDF": [n_rdf],
        "T_seconds": [round(t_seconds, 3)],
        "T_minutes": [round(t_minutes, 3)],
        "DPR": [round(dpr, 4)],
        "TpS": [round(tps, 4)],
        "ADL": [round(adl, 4)]
    }

    df_resultados = pd.DataFrame(resultados_dict)
    df_resultados.to_csv(output_results_csv, index=False, encoding="utf-8")

    print(f"[Éxito] Evaluación completada. Resultados guardados en '{output_results_csv}'.")

    return df_resultados


if __name__ == "__main__":
    # evaluate_efficiency("./predictions", "monitor_results_summary.csv")
    pass