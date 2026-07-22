# GUIA-Madrid-Bench

GUIA-Madrid-Bench is a benchmark for evaluating proposals generating RDF Knowledge Graphs from unstructured data sources relaying on an input ontology. It provides:
- A corpus of 5,388 official academic PDF syllabi from Universidad Politécnica de Madridand their respective RDF graphs, i.e., the gold standard.
- The GUIA ontology and SHACL shapes;
- Effectiveness evaluation scripts;
- Efficiency evaluation scripts;
- Comparative HTML report generators.

The benchmark targets document-level RDF generation: given a PDF document and a target ontology, a system is expected to generate an RDF file that can be parsed, validated, and compared against the corresponding RDF gold standard.

## Repository structure

| Path | Description | Documentation |
|---|---|---|
| `resources/` | Benchmark resources: input PDF corpus, RDF gold standard, GUIA ontology, and SHACL shapes. | [`resources/README.md`](resources/README.md) |
| `effectiveness_scripts/` | Scripts for evaluating the quality of RDF predictions against the gold standard. Includes structural, content, lexical, semantic metrics and comparative HTML reports. | [`effectiveness_scripts/README.md`](effectiveness_scripts/README.md) |
| `efficiency_scripts/` | Scripts for monitoring executions and computing efficiency metrics such as execution time, resource consumption, throughput and correctness-aware efficiency. | [`efficiency_scripts/README.md`](efficiency_scripts/README.md) |

## Benchmark resources

The benchmark resources are located under `resources/`.

They include 5,388 paired PDF and RDF files. Each PDF document has a corresponding RDF gold standard file with the same filename stem and a different extension.

Example:

```text
resources/inputs/corpus/20504112-20BT-2025-26.pdf
resources/gold/20504112-20BT-2025-26.ttl
```

## Evaluation framework

GUIA-Madrid-Bench evaluates RDF generation proposals from two complementary perspectives.

### Effectiveness

Effectiveness metrics evaluate the quality of the generated RDF graphs. They include:

- structural metrics: syntactic consistency, ontology conformance, class hallucination, property hallucination;
- content quantity metrics: expected typed instances, expected properties, expected datatype literals, expected language-tagged literals;
- strict content metrics: precision, recall, F1 and accuracy over predicate-object pairs;
- lexical content similarity: Jaccard, Levenshtein, TF-IDF cosine and Bag-of-Words cosine;
- semantic content similarity: Sentence-BERT and BERTScore.

See [`effectiveness_scripts/README.md`](effectiveness_scripts/README.md).

### Efficiency

Efficiency metrics evaluate the computational cost of RDF generation. They include:

- resource consumption: execution time, CPU, RAM, GPU/VRAM when available, energy and CO2 emissions;
- generation efficiency: documents processing rate, triples per second and average document latency;
- correctness-aware efficiency: valid triples per second, net utility rate, semantic speed index and time-to-target value.

See [`efficiency_scripts/README.md`](efficiency_scripts/README.md).

## Quick start: Evaluate RDF predictions and generate HTML report

### 1. Effectiveness reports

```bash
cd effectiveness_scripts
docker compose build

docker compose run --rm guia-metrics python effectiveness.py effectiveness report \
  --pred-dir /resources/predictions/my_system \
  --gold-dir /resources/gold \
  --ontology /resources/models/ontology.ttl \
  --shapes /resources/models/shapes.ttl \
  --output-dir /resources/reports/my_system
```
```bash
docker compose run --rm guia-metrics python compare_effectiveness_reports_html.py \
  /resources/reports \
  -o /resources/reports/comparative_effectiveness_report.html
```

### 2. Efficiency reports

```bash
cd efficiency_scripts

python run_efficiency.py \
  --pred-dir ../resources/predictions/my_system \
  --gold-dir ../resources/gold \
  --ontology ../resources/ontology.ttl \
  --output-dir ../resources/reports/my_system
```

## How to cite

If you use GUIA-Madrid-Bench in your research, please cite the associated paper:

```bibtex
@article{cimmino2026guiamadridbench,
  title = {GUIA-Madrid-Bench: A benchmark for RDF generation from unstructured data sources in the academic domain},
  author = {Cimmino, Andrea and Amador-Domínguez, Elvira and Mariño-Andrés, Rodrigo and Gayoso-Cabada, Joaquín},
  journal = {Information Processing & Management},
  year = {2026},
  note = {To appear}
}
```


### Acknowledgements
This project has been partially funded by:

 | Project       | Grant |
 |   :---:      |      :---      |
  | <img height="80" alt="guia-logo" src="https://github.com/user-attachments/assets/84dab4ff-c718-4f07-97bf-54c239fe8f28" /> | The Madrid Government (Comunidad de Madrid-Spain) under the Multiannual Agreement with the Universidad Politécnica de Madrid in the Excellence Programme for University Teaching Staff, in the context of the V PRICIT (Regional Programme of Research and Technological Innovation) through the project [GUIA (M230020126A-AJCA)](https://guia-project.github.io/). <br/><img src="https://github.com/user-attachments/assets/152dc6f1-e418-41bc-9c50-88cc88b33525" height="80"/>|
 | <img src="https://malta.linkeddata.es/malta.png" height="80"/> | The [MALTA](https://malta.linkeddata.es/) project, PID2024-159504OB-I00 funded by MICIU/AEI/10.13039/501100011033 |


