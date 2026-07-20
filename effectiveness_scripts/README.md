# GUIA-Madrid-Bench Effectiveness Scripts

This folder contains the scripts required to evaluate RDF predictions in **GUIA-Madrid-Bench** and to visualize the results across several techniques.

It includes two main Python scripts:

```text
effectiveness.py
compare_effectiveness_reports_html.py
```

`effectiveness.py` compares a folder of predicted RDF files against the RDF gold standard and generates CSV reports for each metric family.

`compare_effectiveness_reports_html.py` reads the CSV reports produced for several techniques and generates a single comparative HTML report.

The HTML report is intended to make it easier to inspect the results of multiple experiments together.

## What is evaluated?

The metrics implemented in this repository correspond to the effectiveness metrics defined in the GUIA-Madrid-Bench paper. They evaluate how close a generated RDF graph is to the corresponding RDF gold standard.

The metrics are grouped into the same families used in the paper and in the generated reports.

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

Strict content metrics compare the generated RDF against the gold standard using exact predicate-object matches.

Subjects are ignored during this comparison because different RDF generation systems may create different URIs for the same real-world entities.

This family includes content-quantity metrics:

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

Fuzzy content metrics compare literal values grouped by RDF property. They are useful when the generated literal is not exactly equal to the gold standard literal but is still lexically or semantically similar.

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

## Repository contents

```text
.
├── effectiveness.py
├── compare_effectiveness_reports_html.py
├── guia_metrics/
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── run-docker-all.sh
└── README.md
```

This version intentionally keeps the project focused on effectiveness evaluation:

- semantic content similarity is implemented with Sentence-BERT and BERTScore;
- WMD is not included;
- no legacy aggregate reports are generated;
- no plotting or dashboard dependencies are required;
- no experiment data is bundled with the scripts.

## Expected resources layout

The scripts assume that the benchmark resources are available in a directory named `resources/`.

```text
resources/
├── gold/
│   ├── 20504112-20BT-2025-26.ttl
│   └── ...
├── corpus/
│   ├── 20504112-20BT-2025-26.pdf
│   └── ...
├── models/
│   ├── ontology.ttl
│   └── shapes.ttl
├── predictions/
│   ├── pred_gemma4_base/
│   │   ├── 20504112-20BT-2025-26.ttl
│   │   └── ...
│   └── pred_qwen3.5_base/
│       └── ...
└── reports/
```

Prediction and gold files are matched by filename stem.

For example:

```text
resources/gold/20504112-20BT-2025-26.ttl
resources/predictions/pred_gemma4_base/20504112-20BT-2025-26.ttl
```

The corresponding input PDF may be stored as:

```text
resources/corpus/20504112-20BT-2025-26.pdf
```

## Requirements

All Python dependencies are listed in a single file:

```text
requirements.txt
```

The comparative HTML script uses only the Python standard library, so it does not require additional dependencies beyond those already installed for the evaluation framework.

## Running an experiment with Docker

The recommended way to run the evaluator is through Docker, so that the environment is reproducible.

First, build the image:

```bash
docker compose build
```

Then run one experiment:

```bash
docker compose run --rm guia-metrics python effectiveness.py effectiveness report \
  --pred-dir /resources/predictions/pred_gemma4_base \
  --gold-dir /resources/gold \
  --ontology /resources/models/ontology.ttl \
  --shapes /resources/models/shapes.ttl \
  --output-dir /resources/reports/pred_gemma4_base
```

The command above compares:

```text
/resources/predictions/pred_gemma4_base
```

against:

```text
/resources/gold
```

and writes the results to:

```text
resources/reports/pred_gemma4_base
```

on the host machine.

This works because `docker-compose.yml` mounts the local `./resources` directory inside the container as `/resources`.

### Skipping semantic metrics

By default, the evaluator computes both Sentence-BERT and BERTScore semantic similarity. The first execution may take longer because the models need to be downloaded and cached.

To skip semantic metrics:

```bash
docker compose run --rm guia-metrics python effectiveness.py effectiveness report \
  --pred-dir /resources/predictions/pred_gemma4_base \
  --gold-dir /resources/gold \
  --ontology /resources/models/ontology.ttl \
  --shapes /resources/models/shapes.ttl \
  --output-dir /resources/reports/pred_gemma4_base \
  --semantic-methods none
```

To use only Sentence-BERT:

```bash
docker compose run --rm guia-metrics python effectiveness.py effectiveness report \
  --pred-dir /resources/predictions/pred_gemma4_base \
  --gold-dir /resources/gold \
  --ontology /resources/models/ontology.ttl \
  --shapes /resources/models/shapes.ttl \
  --output-dir /resources/reports/pred_gemma4_base \
  --semantic-methods sentence_bert
```

## Generated files for one experiment

For each technique, `effectiveness.py` writes the following files:

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

The most useful files for reading the results are the three summary files:

```text
effectiveness_structural_summary.csv
effectiveness_strict_content_summary.csv
effectiveness_fuzzy_content_summary.csv
```

`extended-report.txt` contains additional diagnostic information, especially parsing errors and metric failures.

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

The HTML report groups the comparison using the same families as the paper:

```text
Structural metrics
Content quantity metrics
Strict content metrics
Strict content confusion matrix totals
Lexical fuzzy content similarity
Semantic fuzzy content similarity
```

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

To add or remove techniques, edit the `TECHNIQUES` array in `run-docker-all.sh`:

```bash
TECHNIQUES=(
  pred_gemma4_base
  pred_gemma4_refined
  my_new_system
)
```

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
resources/reports/my_new_system/
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
  --pred-dir resources/predictions/pred_gemma4_base \
  --gold-dir resources/gold \
  --ontology resources/models/ontology.ttl \
  --shapes resources/models/shapes.ttl \
  --output-dir resources/reports/pred_gemma4_base
```

Generate the comparative HTML report:

```bash
python compare_effectiveness_reports_html.py \
  resources/reports \
  -o resources/reports/comparative_effectiveness_report.html
```

## Notes

- The evaluator expects Turtle input by default.
- Predictions and gold standards are matched by filename stem.
- RDF files that cannot be parsed receive `syntactic_consistency = false`.
- Metrics that require parsed RDF are left empty for invalid RDF files.
- Details about parsing errors, SHACL validation problems and metric failures are written to `extended-report.txt`.
- The first run with semantic metrics may take longer because Sentence-BERT and BERTScore models need to be downloaded and cached.
- The comparative HTML report is static and can be opened directly in a browser.
