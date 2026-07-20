#!/usr/bin/env bash
set -euo pipefail

# Run all bundled baseline evaluations and then build the comparative HTML report.
# The host ./resources directory is mounted inside the container as /resources.

TECHNIQUES=(
  pred_gemma4_base
  pred_gemma4_refined
  pred_gemma4_spa
  pred_qwen3.5_base
  pred_qwen3.5_refined
  pred_qwen3.5_spa
)

for TECHNIQUE in "${TECHNIQUES[@]}"; do
  docker compose run --rm guia-metrics python effectiveness.py effectiveness report \
    --pred-dir "/resources/predictions/${TECHNIQUE}" \
    --gold-dir /resources/gold \
    --ontology /resources/models/ontology.ttl \
    --shapes /resources/models/shapes.ttl \
    --output-dir "/resources/reports/${TECHNIQUE}"
done

# Generate the comparative HTML report in resources/reports.
docker compose run --rm guia-metrics python compare_effectiveness_reports_html.py \
  /resources/reports \
  -o /resources/reports/comparative_effectiveness_report.html
