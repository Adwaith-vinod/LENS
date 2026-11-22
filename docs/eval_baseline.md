# LENS Retrieval Evaluation Baseline

Recorded on: 2026-11-22
Harness: `tests/test_eval.py`
Corpus: 10 synthetic multiformat files (PDF, DOCX, PPTX, XLSX, CSV, TXT, MD, RTF).

---

## Evaluation Benchmark Queries & Expected Files

| # | Query | Expected Target File | Target Category | Baseline Rank | Top-1 Hit | Top-3 Hit |
|:---|:---|:---|:---|:---:|:---:|:---:|
| 1 | `find me the presentation about docker and kubernetes` | `docker_kubernetes_overview.pptx` | `presentations` | 1 | YES | YES |
| 2 | `document explaining third normal form and BCNF database normalization` | `database_normalization_guide.pdf` | `documents` | 1 | YES | YES |
| 3 | `find the spreadsheet containing employee salary compensation details` | `employee_salary_q4.xlsx` | `spreadsheets` | 1 | YES | YES |
| 4 | `machine learning guide on decision tree splitting and entropy` | `decision_trees_classification.docx` | `documents` | 1 | YES | YES |
| 5 | `presentation discussing convolutional and recurrent neural networks` | `neural_network_architectures.pptx` | `presentations` | 1 | YES | YES |
| 6 | `department budget allocation and quarterly expense forecast spreadsheet` | `financial_budget_2026.csv` | `spreadsheets` | 1 | YES | YES |
| 7 | `reliable transmission control protocol vs user datagram protocol` | `network_protocols_tcp_udp.txt` | `documents` | 1 | YES | YES |
| 8 | `system design article covering reverse proxies and load balancing` | `microservices_load_balancer.md` | `documents` | 1 | YES | YES |
| 9 | `quantum_computing_notes` (Filename-only query) | `quantum_computing_notes.rtf` | `documents` | 1 | YES | YES |
| 10 | `ERR_DATABASE_CONNECTION_POOL_EXHAUSTED` (Exact keyword query) | `incident_postmortem_october.txt` | `documents` | 1 | YES | YES |

---

## Summary Metrics

- **Total Test Cases**: 10
- **Top-1 Hits**: 10 / 10 (**100.0%**)
- **Top-3 Hits**: 10 / 10 (**100.0%**)
- **Average Query Latency**: ~35 ms
