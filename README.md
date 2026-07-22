# GUIA-Madrid-Bench

[![License](https://img.shields.io/github/license/skai-upm/guia-mad-bench)](LICENSE)
![Python](https://img.shields.io/badge/python-3.11-blue)
![RDF](https://img.shields.io/badge/RDF-Turtle-orange)
![Ontology](https://img.shields.io/badge/ontology-GUIA-blueviolet)
![SHACL](https://img.shields.io/badge/validation-SHACL-green)

**GUIA-Madrid-Bench** is a benchmark for evaluating ontology-guided RDF generation from unstructured academic PDF documents.

The benchmark targets **document-level RDF generation**: given an input PDF document and the GUIA ontology, a system is expected to generate one RDF graph serialized in Turtle. The generated RDF is then evaluated against the corresponding RDF gold standard.

GUIA-Madrid-Bench provides:

- a corpus of **5,388 official academic PDF syllabi** from the Universidad Politécnica de Madrid;
- one RDF gold standard graph for each PDF document;
- the [GUIA ontology](https://w3id.org/def/guia) and SHACL shapes;
- scripts for computing effectiveness metrics;
- scripts for computing efficiency metrics;
- HTML report generators for comparing several RDF generation techniques.

The benchmark is method-agnostic. It can be used to evaluate LLM-based systems, rule-based extractors, information extraction pipelines, retrieval-augmented generation approaches, ontology-aware prompting strategies, fine-tuned models, or hybrid systems.

## Repository structure

| Path | Description | Documentation |
|---|---|---|
| [`resources/`](resources/) | Benchmark resources: input PDF corpus, RDF gold standard, GUIA ontology, and SHACL shapes. | [`resources/README.md`](resources/README.md) |
| [`effectiveness_scripts/`](effectiveness_scripts/) | Scripts for evaluating the quality of RDF predictions against the gold standard. Includes structural, content, lexical, semantic metrics, and an HTML comparison report. | [`effectiveness_scripts/README.md`](effectiveness_scripts/README.md) |
| [`efficiency_scripts/`](efficiency_scripts/) | Scripts for monitoring executions and computing efficiency metrics such as execution time, resource consumption, throughput, and correctness-aware efficiency. | [`efficiency_scripts/README.md`](efficiency_scripts/README.md) |

## Benchmark resources

The benchmark resources are located under [`resources/`](resources/).

The dataset contains **5,388 paired PDF/RDF resources**. Each PDF document has a corresponding RDF gold standard file with the same filename stem and a different extension.

Example:

```text
resources/inputs/corpus/20504112-20BT-2025-26.pdf
resources/gold/20504112-20BT-2025-26.ttl
```

The PDF corpus was extracted from official teaching guides of the **Universidad Politécnica de Madrid** for the academic year **2025–2026**. The RDF gold standards were generated from structured institutional information and aligned with the GUIA ontology.

The GUIA ontology is published at:

```text
https://w3id.org/def/guia
```

The ontology source code is maintained at:

```text
https://github.com/guia-project/guia-ontology
```

## Evaluation framework

GUIA-Madrid-Bench evaluates RDF generation proposals from two complementary perspectives: **effectiveness** and **efficiency**.

### Effectiveness

Effectiveness metrics evaluate the quality of the generated RDF graphs with respect to the RDF gold standard.

They are grouped as follows:

| Group | Metrics | Purpose |
|---|---|---|
| Structural metrics | `syntactic_consistency`, `ontology_conformance`, `class_hallucination`, `property_hallucination` | Check whether the generated RDF is valid Turtle, SHACL-compliant, and uses only terms defined in the ontology. |
| Content quantity metrics | `expected_typed_instances`, `expected_properties`, `expected_datatype_literals`, `expected_language_tagged_literals` | Compare the amount of generated RDF content with the amount expected in the gold standard. |
| Strict content metrics | `strict_precision`, `strict_recall`, `strict_f1`, `strict_accuracy` | Compare exact predicate-object pairs while ignoring subjects. |
| Lexical content similarity | Jaccard, Levenshtein, TF-IDF cosine, Bag-of-Words cosine | Compare generated and expected literals using lexical similarity. |
| Semantic content similarity | Sentence-BERT, BERTScore | Compare generated and expected literals using semantic similarity. |

See [`effectiveness_scripts/README.md`](effectiveness_scripts/README.md) for full execution instructions.

### Efficiency

Efficiency metrics evaluate the computational cost and productivity of RDF generation systems.

They are grouped as follows:

| Group | Metrics | Purpose |
|---|---|---|
| Resource consumption | execution time, CPU, RAM, GPU/VRAM when available, energy, CO2 emissions | Measure the computational resources required by a generation process. |
| Generation efficiency | documents processing rate, triples per second, average document latency | Measure how fast RDF files and triples are generated. |
| Correctness-aware efficiency | valid triples per second, net utility rate, semantic speed index, time-to-target value | Combine generation speed with correctness and quality indicators. |

See [`efficiency_scripts/README.md`](efficiency_scripts/README.md) for full execution instructions.

## Quick start

The following example evaluates one RDF generation system and then creates a comparative HTML report.

### 1. Prepare predictions

Place your generated RDF files under:

```text
resources/predictions/my_system/
```

Each prediction must be a Turtle file whose name matches the corresponding gold standard file.

Example:

```text
resources/gold/20504112-20BT-2025-26.ttl
resources/predictions/my_system/20504112-20BT-2025-26.ttl
```

### 2. Run effectiveness evaluation with Docker

From the repository root:

```bash
cd effectiveness_scripts
docker compose build

docker compose run --rm guia-metrics python effectiveness.py effectiveness report   --pred-dir /resources/predictions/my_system   --gold-dir /resources/gold   --ontology /resources/ontology.ttl   --shapes /resources/shapes.ttl   --output-dir /resources/reports/my_system
```

The reports will be written to:

```text
resources/reports/my_system/
```

### 3. Generate the comparative effectiveness HTML report

After evaluating two or more systems, run:

```bash
docker compose run --rm guia-metrics python compare_effectiveness_reports_html.py   /resources/reports   -o /resources/reports/comparative_effectiveness_report.html
```

The HTML file will be available at:

```text
resources/reports/comparative_effectiveness_report.html
```

Open it in a browser to compare the results of the evaluated systems.

### 4. Compute efficiency metrics

After running your RDF generation process with the monitoring script (monitor.py), compute efficiency metrics as follows:

```bash
cd ../efficiency_scripts

python run_efficiency.py   --pred-dir ../resources/predictions/my_system   --gold-dir ../resources/gold   --ontology ../resources/ontology.ttl   --output-dir ../resources/reports/my_system
```

See [`efficiency_scripts/README.md`](efficiency_scripts/README.md) for the complete workflow.

## Evaluating your own RDF generation system

To evaluate a new system:

1. Generate one Turtle file per input PDF.
2. Store the predictions in a new folder under `resources/predictions/`.
3. Preserve the filename stem used by the gold standard.
4. Run the effectiveness evaluator.
5. Optionally run the efficiency evaluator.
6. Generate the comparative HTML reports.

Example structure:

```text
resources/
├── gold/
│   └── 20504112-20BT-2025-26.ttl
├── inputs/
│   └── corpus/
│       └── 20504112-20BT-2025-26.pdf
├── predictions/
│   └── my_system/
│       └── 20504112-20BT-2025-26.ttl
└── reports/
    └── my_system/
```


## License

This repository is distributed under the Apache License 2.0. See [`LICENSE`](LICENSE).



