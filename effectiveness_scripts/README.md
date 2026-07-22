# GUIA-Madrid-Bench Effectiveness Scripts

This folder contains the scripts required to evaluate RDF predictions in **GUIA-Madrid-Bench** and to visualize effectiveness results across several techniques.

It includes two main Python scripts:

```text
effectiveness.py
compare_effectiveness_reports_html.py
```

`effectiveness.py` compares a folder of predicted RDF files against the RDF gold standard and generates CSV reports for each metric family.

`compare_effectiveness_reports_html.py` reads the CSV reports produced for several techniques and generates a single comparative HTML report. This report is intended to make it easier to inspect the results of multiple experiments together.

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

### Structural metrics

```text
syntactic_consistency
ontology_conformance
class_hallucination
property_hallucination
```

Generated files:

```text
effectiveness_structural_results.csv
effectiveness_structural_summary.csv
```

### Strict content metrics

Strict content metrics compare generated RDF against the gold standard using exact predicate-object matches. Subjects are ignored during this comparison.

Content-quantity metrics:

```text
expected_typed_instances
expected_properties
expected_datatype_literals
expected_language_tagged_literals
```

Strict predicate-object metrics:

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

The scripts assume that benchmark resources are available in this repository-level `resources/` folder.

```text
resources/
├── gold/
├── inputs/
│   └── corpus/
├── ontology.ttl
├── shapes.ttl
├── predictions/
└── reports/
```

Prediction and gold files are matched by filename stem.

```text
resources/gold/20504112-20BT-2025-26.ttl
resources/predictions/pred_gemma4_base/20504112-20BT-2025-26.ttl
```

## Requirements

All Python dependencies are listed in:

```text
requirements.txt
```

The comparative HTML script uses only the Python standard library.

## Running an experiment with Docker

From this folder:

```bash
docker compose build
```

Then run one experiment:

```bash
docker compose run --rm guia-metrics python effectiveness.py effectiveness report   --pred-dir /resources/predictions/pred_gemma4_base   --gold-dir /resources/gold   --ontology /resources/ontology.ttl   --shapes /resources/shapes.ttl   --output-dir /resources/reports/pred_gemma4_base
```

The Docker Compose configuration must mount the repository-level `resources/` folder inside the container as `/resources`.

### Skipping semantic metrics

```bash
docker compose run --rm guia-metrics python effectiveness.py effectiveness report   --pred-dir /resources/predictions/pred_gemma4_base   --gold-dir /resources/gold   --ontology /resources/ontology.ttl   --shapes /resources/shapes.ttl   --output-dir /resources/reports/pred_gemma4_base   --semantic-methods none
```

## Generated files for one experiment

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

## Interpreting results

Coverage indicates the proportion of documents for which a metric could be computed.

Metrics that require parsed RDF are computed only for syntactically valid predictions. Therefore, scores must always be interpreted together with:

```text
syntactic_consistency
failure_rate
coverage
```

A high score with very low coverage may not represent the global behaviour of a technique.

## Generating the comparative HTML report with Docker

After running two or more experiments, generate the comparative HTML report with:

```bash
docker compose run --rm guia-metrics python compare_effectiveness_reports_html.py   /resources/reports   -o /resources/reports/comparative_effectiveness_report.html
```

The generated file will be available at:

```text
resources/reports/comparative_effectiveness_report.html
```

The HTML report groups the comparison as:

```text
Structural metrics
Content quantity metrics
Strict content metrics
Strict content confusion matrix totals
Lexical fuzzy content similarity
Semantic fuzzy content similarity
```

## Running all predefined experiments

```bash
./run-docker-all.sh
```

Edit the `TECHNIQUES` array in `run-docker-all.sh` to add or remove prediction folders.

## Local execution without Docker

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

Run one evaluation:

```bash
python effectiveness.py effectiveness report   --pred-dir ../resources/predictions/pred_gemma4_base   --gold-dir ../resources/gold   --ontology ../resources/ontology.ttl   --shapes ../resources/shapes.ttl   --output-dir ../resources/reports/pred_gemma4_base
```

Generate the comparative HTML report:

```bash
python compare_effectiveness_reports_html.py   ../resources/reports   -o ../resources/reports/comparative_effectiveness_report.html
```

## Notes

- The evaluator expects Turtle input by default.
- Predictions and gold standards are matched by filename stem.
- RDF files that cannot be parsed receive `syntactic_consistency = false`.
- Metrics that require parsed RDF are left empty for invalid RDF files.
- Details about parsing errors, SHACL validation problems and metric failures are written to `extended-report.txt`.
- The first run with semantic metrics may take longer because Sentence-BERT and BERTScore models need to be downloaded and cached.
- The comparative HTML report is static and can be opened directly in a browser.

# GUIA-Madrid-Bench Resources

This folder contains the benchmark resources used by **GUIA-Madrid-Bench**.

The resources are part of the **GUIA project** and include:

- the input PDF corpus;
- the RDF gold standard;
- the GUIA ontology;
- the SHACL shapes used for validation.

The corpus was extracted from official teaching guides of the **Universidad Politécnica de Madrid (UPM)** for the academic year **2025–2026**.

## Dataset overview

The dataset contains **5,388 paired resources**. Each PDF document has a corresponding RDF gold standard file with the same filename stem and a different extension.

Example:

```text
inputs/corpus/20504112-20BT-2025-26.pdf
gold/20504112-20BT-2025-26.ttl
```

This naming convention allows the evaluation tools to automatically match each input document with its expected RDF representation.

## Directory structure

```text
resources/
├── inputs/
│   └── corpus/
│       ├── 20504112-20BT-2025-26.pdf
│       └── ...
├── gold/
│   ├── 20504112-20BT-2025-26.ttl
│   └── ...
├── ontology.ttl
├── shapes.ttl
└── README.md
```

## Resource description

### `inputs/corpus/`

This folder contains the input documents of the benchmark.

Each file is a PDF teaching guide from the Universidad Politécnica de Madrid for the academic year 2025–2026. These PDFs are the unstructured source documents from which RDF generation systems are expected to extract information.

### `gold/`

This folder contains the RDF gold standard files in Turtle format.

Each `.ttl` file represents the expected RDF graph associated with one PDF document from the corpus. The RDF files describe the academic information contained in the teaching guides according to the GUIA ontology.

For every file:

```text
inputs/corpus/<document-id>.pdf
```

there should be a corresponding file:

```text
gold/<document-id>.ttl
```

### `ontology.ttl`

This file contains the GUIA ontology used to model the academic information represented in the RDF gold standard.

The ontology is published at:

```text
https://w3id.org/def/guia
```

The ontology source code is available at:

```text
https://github.com/guia-project/guia-ontology
```

### `shapes.ttl`

This file contains the SHACL shapes used to validate RDF graphs against the expected structure of the GUIA ontology.

The shapes were generated with **Astrea**, a tool for generating SHACL shapes from ontologies:

```text
https://astrea.linkeddata.es/
```

## Naming convention

The benchmark relies on a strict filename convention. Each PDF document and its RDF gold standard must share the same filename stem.

Correct example:

```text
inputs/corpus/20504112-20BT-2025-26.pdf
gold/20504112-20BT-2025-26.ttl
```

Incorrect example:

```text
inputs/corpus/20504112-20BT-2025-26.pdf
gold/20504112.ttl
```

This convention is required so that the evaluation scripts can automatically associate each generated RDF prediction with its corresponding gold standard.

## Usage in the evaluation framework

A typical effectiveness evaluation expects the following resources:

```bash
python effectiveness.py effectiveness report   --pred-dir resources/predictions/my_system   --gold-dir resources/gold   --ontology resources/ontology.ttl   --shapes resources/shapes.ttl   --output-dir resources/reports/my_system
```

Where:

- `--pred-dir` contains the RDF files generated by the evaluated system;
- `--gold-dir` points to the RDF gold standard;
- `--ontology` points to the GUIA ontology;
- `--shapes` points to the SHACL shapes;
- `--output-dir` is the directory where the evaluation reports will be written.

## Recommended checks

Before running an evaluation, verify that:

1. every `.ttl` file in `gold/` has a matching `.pdf` file in `inputs/corpus/`;
2. every RDF file in `gold/` can be parsed as valid Turtle;
3. the RDF gold standard only uses classes and properties defined in the GUIA ontology;
4. the SHACL shapes are aligned with the current version of the ontology and the gold standard.

Useful shell checks:

```bash
find gold -name "*.ttl" | wc -l
find inputs/corpus -name "*.pdf" | wc -l
```

## Data statement

The corpus contains official teaching guides from Universidad Politécnica de Madrid for the academic year 2025–2026. The documents are provided as benchmark inputs for evaluating RDF generation from academic PDFs. Users should preserve filenames because file matching relies on the filename stem.

### Acknowledgements
This project has been partially funded by:

 | Project       | Grant |
 |   :---:      |      :---      |
  | <img height="80" alt="guia-logo" src="https://github.com/user-attachments/assets/84dab4ff-c718-4f07-97bf-54c239fe8f28" /> | The Madrid Government (Comunidad de Madrid-Spain) under the Multiannual Agreement with the Universidad Politécnica de Madrid in the Excellence Programme for University Teaching Staff, in the context of the V PRICIT (Regional Programme of Research and Technological Innovation) through the project [GUIA (M230020126A-AJCA)](https://guia-project.github.io/). <br/><img src="https://github.com/user-attachments/assets/152dc6f1-e418-41bc-9c50-88cc88b33525" height="80"/>|
 | <img src="https://malta.linkeddata.es/malta.png" height="80"/> | The [MALTA](https://malta.linkeddata.es/) project, PID2024-159504OB-I00 funded by MICIU/AEI/10.13039/501100011033 |


