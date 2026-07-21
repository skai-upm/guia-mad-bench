# Efficiency Evaluation (GUIA-MAD-BENCH)

This module is responsible for exclusively calculating the **Generation Efficiency Metrics** and **Correctness Efficiency Metrics** of RDF extraction proposals. It is designed to provide a computational and productivity evaluation without incurring the high computational costs of strict semantic effectiveness metrics.

## 📋 Prerequisites

Before running this script, it is **strictly necessary** to have run the system monitor (`monitor.py`) during your model's inference.

The efficiency script will look for the `monitor_results_summary.csv` file in the output directory to extract the total execution time ($T_{seconds}$). **Without this file, the metrics cannot be calculated.**

## 🚀 Usage

To execute the efficiency calculation, use the `run_efficiency.py` script by passing the paths to the generated data (predictions), the gold standard, and the ontology.

```bash
python run_efficiency.py \
  --pred-dir path/to/predictions_ttl \
  --gold-dir path/to/gold_standard_ttl \
  --ontology path/to/ontology.owl \
  --output-dir path/to/results

```
