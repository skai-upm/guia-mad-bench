# Evaluación de Eficiencia (GUIA-MAD-BENCH)

Este módulo se encarga de calcular exclusivamente las **Métricas de Eficiencia de Generación** y **Métricas de Eficiencia de Correctitud** de las propuestas de extracción RDF. Está diseñado para ofrecer una evaluación computacional y de productividad sin incurrir en los altos costes de cálculo de las métricas semánticas estrictas de efectividad.

## 📋 Prerrequisitos

Antes de ejecutar este script, es **estrictamente necesario** haber ejecutado el monitor de sistema (`monitor.py`) durante la inferencia de tu modelo. 

El script de eficiencia buscará el archivo `monitor_results_summary.csv` en el directorio de salida para extraer el tiempo total de ejecución ($T_{seconds}$). Sin este archivo, las métricas no se podrán calcular.

## 🚀 Uso

Para ejecutar el cálculo de eficiencia, utiliza el script `run_efficiency.py` pasando las rutas a los datos generados (predicciones), el estándar de oro (Gold Standard) y la ontología.

```bash
python run_efficiency.py \
  --pred-dir ruta/a/predicciones_ttl \
  --gold-dir ruta/a/gold_standard_ttl \
  --ontology ruta/a/ontologia.owl \
  --output-dir ruta/a/resultados