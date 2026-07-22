# GUIA-Madrid-Bench Effectiveness Scripts

This folder contains the scripts required to evaluate RDF predictions in **GUIA-Madrid-Bench** and to visualize effectiveness results across several techniques.

It includes two main Python scripts:

```text
effectiveness.py
compare_effectiveness_reports_html.py
```

`effectiveness.py` compares a folder of predicted RDF files against the RDF gold standard and generates CSV reports for each metric family.

`compare_effectiveness_reports_html.py` reads the CSV reports produced for several techniques and generates a single comparative HTML report. This report is intended to make it easier to inspect the results of multiple experiments together.

The scripts can be used in two different scenarios:

1. to evaluate a new RDF generation technique against GUIA-Madrid-Bench;
2. to reproduce the effectiveness reports of the baseline experiments described in the GUIA-Madrid-Bench paper.

## Inputs and outputs

Inputs:

- predicted RDF files in Turtle format;
- RDF gold standard files in Turtle format;
- the GUIA ontology;
- SHACL shapes generated from the ontology.

Outputs:

- document-level CSV reports;
- aggregated CSV summaries;
- a strict-content confusion matrix;
- an extended diagnostic report;
- optionally, a comparative HTML report across several techniques.

## Metrics

The metrics implemented in this folder correspond to the effectiveness metrics defined in the GUIA-Madrid-Bench paper.

They are grouped into the same metric families used in the paper and in the generated reports.

### Structural metrics

Structural metrics evaluate whether the generated RDF is formally valid and aligned with the expected ontology and SHACL constraints.

They include:

```text
syntactic_consistency
ontology_conformance
class_hallucination
property_hallucination
```

These metrics answer questions such as:

- Can the predicted Turtle file be parsed as valid RDF?
- Does the RDF graph conform to the SHACL shapes?
- Does the RDF graph use classes that are not defined in the GUIA ontology?
- Does the RDF graph use properties that are not defined in the GUIA ontology?

Generated files:

```text
effectiveness_structural_results.csv
effectiveness_structural_summary.csv
```

### Strict content metrics

Strict content metrics compare generated RDF against the gold standard using exact predicate-object matches. Subjects are ignored during this comparison because different RDF generation systems may create different URIs for the same real-world entities.

This metric family includes content-quantity metrics:

```text
expected_typed_instances
expected_properties
expected_datatype_literals
expected_language_tagged_literals
```

and strict predicate-object comparison metrics:

```text
strict_precision
strict_recall
strict_f1
strict_accuracy
```

Generated files:

```text
effectiveness_strict_content_results.csv
effectiveness_strict_content_summary.csv
effectiveness_strict_content_confusion_matrix.csv
```

### Fuzzy content metrics

Fuzzy content metrics compare literal values grouped by RDF property.

They are useful when the generated literal is not exactly equal to the gold standard literal but is still lexically or semantically similar.

Lexical strategies:

```text
Jaccard
Levenshtein
TF-IDF cosine
Bag-of-Words cosine
```

Semantic strategies:

```text
Sentence-BERT
BERTScore
```

Generated files:

```text
effectiveness_fuzzy_content_results.csv
effectiveness_fuzzy_content_summary.csv
```

## Expected resources layout

The scripts assume that benchmark resources are available in the repository-level `resources/` folder.

```text
resources/
├── gold/
│   ├── 20504112-20BT-2025-26.ttl
│   └── ...
├── inputs/
│   └── corpus/
│       ├── 20504112-20BT-2025-26.pdf
│       └── ...
├── ontology.ttl
├── shapes.ttl
├── predictions/
│   ├── pred_gemma4_base/
│   │   ├── 20504112-20BT-2025-26.ttl
│   │   └── ...
│   └── pred_qwen3.5_base/
│       └── ...
└── reports/
```

Prediction and gold files are matched by filename stem.

Example:

```text
resources/gold/20504112-20BT-2025-26.ttl
resources/predictions/pred_gemma4_base/20504112-20BT-2025-26.ttl
```

The corresponding input PDF may be stored as:

```text
resources/inputs/corpus/20504112-20BT-2025-26.pdf
```

## Requirements

All Python dependencies are listed in:

```text
requirements.txt
```

The comparative HTML script uses only the Python standard library.

## Running an experiment with Docker

The recommended way to run the evaluator is through Docker.

From this folder, build the image:

```bash
docker compose build
```

Then run one experiment:

```bash
docker compose run --rm guia-metrics python effectiveness.py effectiveness report \
  --pred-dir /resources/predictions/pred_gemma4_base \
  --gold-dir /resources/gold \
  --ontology /resources/ontology.ttl \
  --shapes /resources/shapes.ttl \
  --output-dir /resources/reports/pred_gemma4_base
```

The command compares:

```text
/resources/predictions/pred_gemma4_base
```

against:

```text
/resources/gold
```

and writes the generated reports to:

```text
resources/reports/pred_gemma4_base/
```

on the host machine.

The Docker Compose configuration must mount the repository-level `resources/` folder inside the container as `/resources`.

If this folder is executed from inside `effectiveness_scripts/`, the volume in `docker-compose.yml` should point to the repository-level resources folder:

```yaml
volumes:
  - ../resources:/resources
```

### Skipping semantic metrics

By default, the evaluator computes both Sentence-BERT and BERTScore semantic similarity. The first execution may take longer because the models need to be downloaded and cached.

To skip semantic metrics:

```bash
docker compose run --rm guia-metrics python effectiveness.py effectiveness report \
  --pred-dir /resources/predictions/pred_gemma4_base \
  --gold-dir /resources/gold \
  --ontology /resources/ontology.ttl \
  --shapes /resources/shapes.ttl \
  --output-dir /resources/reports/pred_gemma4_base \
  --semantic-methods none
```

### Using only Sentence-BERT

```bash
docker compose run --rm guia-metrics python effectiveness.py effectiveness report \
  --pred-dir /resources/predictions/pred_gemma4_base \
  --gold-dir /resources/gold \
  --ontology /resources/ontology.ttl \
  --shapes /resources/shapes.ttl \
  --output-dir /resources/reports/pred_gemma4_base \
  --semantic-methods sentence_bert
```

## Reproducing the effectiveness reports from the paper experiments

This folder also includes the scripts and configuration required to reproduce the effectiveness reports for the baseline experiments reported in the GUIA-Madrid-Bench paper.

The experiments compare the RDF predictions generated by different model and prompt configurations against the GUIA-Madrid-Bench RDF gold standard.

The predefined experiment folders are:

```text
pred_gemma4_base
pred_gemma4_refined
pred_gemma4_spa
pred_qwen3.5_base
pred_qwen3.5_refined
pred_qwen3.5_spa
```

These folders correspond to the six baseline experiments described in the paper:

| Experiment | Model | Prompt | Predictions folder |
|---|---|---|---|
| E1 | Qwen 3.5:4B | Baseline prompt | `pred_qwen3.5_base` |
| E2 | Qwen 3.5:4B | Refined prompt | `pred_qwen3.5_refined` |
| E3 | Qwen 3.5:4B | Spanish prompt | `pred_qwen3.5_spa` |
| E4 | Gemma4:26B | Baseline prompt | `pred_gemma4_base` |
| E5 | Gemma4:26B | Refined prompt | `pred_gemma4_refined` |
| E6 | Gemma4:26B | Spanish prompt | `pred_gemma4_spa` |

Each prediction folder must contain one Turtle file per evaluated document. Prediction files must preserve the same filename stem as the corresponding gold standard file.

Example:

```text
resources/gold/20504112-20BT-2025-26.ttl
resources/predictions/pred_gemma4_base/20504112-20BT-2025-26.ttl
```

The expected repository-level layout is:

```text
resources/
├── gold/
│   ├── 20504112-20BT-2025-26.ttl
│   └── ...
├── inputs/
│   └── corpus/
│       ├── 20504112-20BT-2025-26.pdf
│       └── ...
├── ontology.ttl
├── shapes.ttl
├── predictions/
│   ├── pred_gemma4_base/
│   ├── pred_gemma4_refined/
│   ├── pred_gemma4_spa/
│   ├── pred_qwen3.5_base/
│   ├── pred_qwen3.5_refined/
│   └── pred_qwen3.5_spa/
└── reports/
```

### Run one paper experiment

To compute the effectiveness report for one experiment, run:

```bash
docker compose run --rm guia-metrics python effectiveness.py effectiveness report \
  --pred-dir /resources/predictions/pred_gemma4_base \
  --gold-dir /resources/gold \
  --ontology /resources/ontology.ttl \
  --shapes /resources/shapes.ttl \
  --output-dir /resources/reports/pred_gemma4_base
```

This command compares the predictions in:

```text
/resources/predictions/pred_gemma4_base
```

against the gold standard in:

```text
/resources/gold
```

and writes the generated reports to:

```text
resources/reports/pred_gemma4_base/
```

The output folder will contain:

```text
effectiveness_results.csv
effectiveness_structural_results.csv
effectiveness_structural_summary.csv
effectiveness_strict_content_results.csv
effectiveness_strict_content_summary.csv
effectiveness_strict_content_confusion_matrix.csv
effectiveness_fuzzy_content_results.csv
effectiveness_fuzzy_content_summary.csv
extended-report.txt
```

### Run all paper experiments

To reproduce the effectiveness reports for all predefined experiments, run:

```bash
./run-docker-all.sh
```

This script evaluates all predefined prediction folders and writes one report folder per experiment under:

```text
resources/reports/
```

The expected output is:

```text
resources/reports/
├── pred_gemma4_base/
├── pred_gemma4_refined/
├── pred_gemma4_spa/
├── pred_qwen3.5_base/
├── pred_qwen3.5_refined/
├── pred_qwen3.5_spa/
└── comparative_effectiveness_report.html
```

At the end of the execution, the script also generates the comparative HTML report:

```text
resources/reports/comparative_effectiveness_report.html
```

Open this file in a browser to compare the effectiveness results of all baseline experiments.

### Generate only the comparative HTML report

If the CSV reports have already been generated, the comparative HTML can be regenerated without recomputing the metrics:

```bash
docker compose run --rm guia-metrics python compare_effectiveness_reports_html.py \
  /resources/reports \
  -o /resources/reports/comparative_effectiveness_report.html
```

The HTML report groups the metrics according to the same families used in the paper:

```text
Structural metrics
Content quantity metrics
Strict content metrics
Strict content confusion matrix totals
Lexical fuzzy content similarity
Semantic fuzzy content similarity
```

## Generated files for one experiment

For each technique, `effectiveness.py` writes:

```text
effectiveness_results.csv
effectiveness_structural_results.csv
effectiveness_structural_summary.csv
effectiveness_strict_content_results.csv
effectiveness_strict_content_summary.csv
effectiveness_strict_content_confusion_matrix.csv
effectiveness_fuzzy_content_results.csv
effectiveness_fuzzy_content_summary.csv
extended-report.txt
```

The most useful files for reading the results are:

```text
effectiveness_structural_summary.csv
effectiveness_strict_content_summary.csv
effectiveness_fuzzy_content_summary.csv
```

`extended-report.txt` contains additional diagnostic information, especially parsing errors, SHACL validation problems, and metric failures.

## Interpreting results

Coverage indicates the proportion of documents for which a metric could be computed.

Some metrics can only be computed when the generated RDF file is syntactically valid. Therefore, scores must always be interpreted together with:

```text
syntactic_consistency
failure_rate
coverage
```

In particular, when comparing the paper experiments, it is recommended to inspect these values together:

```text
syntactic_consistency
failure_rate
coverage
strict_precision
strict_recall
strict_f1
lexical similarity scores
semantic similarity scores
```

A high score with very low coverage may not represent the global behaviour of a technique.

For example, a model may obtain a high strict precision score on a small number of valid RDF files while failing to generate parseable Turtle for many documents. The comparative HTML report is intended to make this trade-off easier to inspect across experiments.

Strict content metrics provide exact predicate-object comparison. Lexical and semantic similarity metrics are complementary: they help identify near-correct literal values that do not match the gold standard exactly.

## Generating the comparative HTML report with Docker

After running two or more experiments, the `resources/reports/` folder should contain one subfolder per technique.

Example:

```text
resources/reports/
├── pred_gemma4_base/
│   ├── effectiveness_structural_summary.csv
│   ├── effectiveness_strict_content_summary.csv
│   ├── effectiveness_strict_content_confusion_matrix.csv
│   └── effectiveness_fuzzy_content_summary.csv
├── pred_gemma4_refined/
│   └── ...
└── pred_qwen3.5_base/
    └── ...
```

To generate the comparative HTML report:

```bash
docker compose run --rm guia-metrics python compare_effectiveness_reports_html.py \
  /resources/reports \
  -o /resources/reports/comparative_effectiveness_report.html
```

The generated file will be available on the host at:

```text
resources/reports/comparative_effectiveness_report.html
```

Open this file in a browser to inspect the results.

The script automatically detects technique folders under `resources/reports/`, so new experiments can be added simply by creating a new subfolder with the corresponding CSV reports.

## Running all predefined experiments

The helper script `run-docker-all.sh` runs several predefined prediction folders and then generates the comparative HTML report.

Run:

```bash
./run-docker-all.sh
```

The script currently evaluates:

```text
pred_gemma4_base
pred_gemma4_refined
pred_gemma4_spa
pred_qwen3.5_base
pred_qwen3.5_refined
pred_qwen3.5_spa
```

To add or remove techniques, edit the `TECHNIQUES` array in `run-docker-all.sh`.

Each listed technique must have a matching folder under:

```text
resources/predictions/
```

For example:

```text
resources/predictions/my_new_system/
```

The generated reports will be written to:

```text
resources/reports/<technique>/
```

and the final comparative HTML will be written to:

```text
resources/reports/comparative_effectiveness_report.html
```

## Local execution without Docker

Docker is recommended, but the scripts can also be executed locally.

Create a virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

Run one evaluation:

```bash
python effectiveness.py effectiveness report \
  --pred-dir ../resources/predictions/pred_gemma4_base \
  --gold-dir ../resources/gold \
  --ontology ../resources/ontology.ttl \
  --shapes ../resources/shapes.ttl \
  --output-dir ../resources/reports/pred_gemma4_base
```

Generate the comparative HTML report:

```bash
python compare_effectiveness_reports_html.py \
  ../resources/reports \
  -o ../resources/reports/comparative_effectiveness_report.html
```

## Notes

- The evaluator expects Turtle input by default.
- Predictions and gold standards are matched by filename stem.
- RDF files that cannot be parsed receive `syntactic_consistency = false`.
- Metrics that require parsed RDF are left empty for invalid RDF files.
- Details about parsing errors, SHACL validation problems, and metric failures are written to `extended-report.txt`.
- The first run with semantic metrics may take longer because Sentence-BERT and BERTScore models need to be downloaded and cached.
- The comparative HTML report is static and can be opened directly in a browser.



