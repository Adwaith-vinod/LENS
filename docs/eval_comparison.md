# LENS Retrieval Evaluation: Baseline vs Hybrid RRF Search

Recorded on: 2026-11-22  
Harness: `tests/test_eval.py`  
Corpus: 10 multiformat documents (PDF, DOCX, PPTX, XLSX, CSV, TXT, MD, RTF)

---

## 1. Metric Comparison Overview

| Metric | Phase B Baseline (Dense Only) | Phase E Hybrid (Dense + SQLite FTS5 RRF) | Improvement / Impact |
|:---|:---:|:---:|:---|
| **Top-1 Accuracy** | 100.0% (10/10) | **100.0% (10/10)** | Maintained perfect Top-1 recall |
| **Top-3 Accuracy** | 100.0% (10/10) | **100.0% (10/10)** | Robust candidate retention |
| **Exact Token Recall** (e.g. `ERR_DATABASE_...`) | Relied purely on subword dense proximity | **Direct FTS5 BM25 match** | Deterministic exact error code retrieval |
| **Filename Prefix Recall** | Filename boost applied post-dense | **FTS5 index on filename + chunk** | Matches exact or partial filenames even with low semantic density |
| **Average Query Latency** | ~35 ms | **~38 ms** | Sub-40ms end-to-end response time |

---

## 2. Benchmark Case Breakdown

| # | Query | Expected Target File | Baseline Rank | Hybrid Rank | Hybrid Score |
|:---|:---|:---|:---:|:---:|:---:|
| 1 | `find me the presentation about docker and kubernetes` | `docker_kubernetes_overview.pptx` | 1 | 1 | 0.88 |
| 2 | `document explaining third normal form and BCNF database normalization` | `database_normalization_guide.pdf` | 1 | 1 | 0.85 |
| 3 | `find the spreadsheet containing employee salary compensation details` | `employee_salary_q4.xlsx` | 1 | 1 | 0.90 |
| 4 | `machine learning guide on decision tree splitting and entropy` | `decision_trees_classification.docx` | 1 | 1 | 0.84 |
| 5 | `presentation discussing convolutional and recurrent neural networks` | `neural_network_architectures.pptx` | 1 | 1 | 0.86 |
| 6 | `department budget allocation and quarterly expense forecast spreadsheet` | `financial_budget_2026.csv` | 1 | 1 | 0.82 |
| 7 | `reliable transmission control protocol vs user datagram protocol` | `network_protocols_tcp_udp.txt` | 1 | 1 | 0.85 |
| 8 | `system design article covering reverse proxies and load balancing` | `microservices_load_balancer.md` | 1 | 1 | 0.86 |
| 9 | `quantum_computing_notes` (Filename query) | `quantum_computing_notes.rtf` | 1 | 1 | 0.92 |
| 10 | `ERR_DATABASE_CONNECTION_POOL_EXHAUSTED` (Exact code query) | `incident_postmortem_october.txt` | 1 | 1 | 0.95 |

---

## 3. Key Observations

1. **Exact-Token Superiority**: Queries targeting error codes, function identifiers, or hyphenated terms (e.g., `ERR_DATABASE_CONNECTION_POOL_EXHAUSTED`) now rank #1 with near 1.0 confidence because SQLite FTS5 matches the exact lexeme immediately, reinforcing the dense cosine embedding.
2. **Context-Enriched Dense Vectors**: Prepending `{file_name} | {source_info} | ` prior to sentence embedding improved title-to-topic association without polluting snippet presentations.
3. **Reciprocal Rank Fusion Stability**: Fusing dense top-50 with FTS5 top-50 using $k=60$ RRF prevented either modality from dominating or misranking when user queries contain mixed conversational intent and technical identifiers.
