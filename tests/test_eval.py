import os
import unittest
import tempfile
from pathlib import Path
import pymupdf
from docx import Document
from pptx import Presentation
import openpyxl

from backend.storage.db import DatabaseManager
from backend.storage.vector_store import PersistentVectorStore
from backend.indexing.indexer import LensIndexer
from backend.search.engine import SearchEngine


class TestRetrievalEval(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.root = Path(cls.temp_dir.name)
        cls.docs_dir = cls.root / "eval_docs"
        cls.docs_dir.mkdir(parents=True, exist_ok=True)

        cls.db = DatabaseManager(cls.root / "eval.db")
        cls.vector_store = PersistentVectorStore(cls.root / "eval.index", dimension=384)

        # 1. PPTX: Docker & Kubernetes
        p1 = cls.docs_dir / "docker_kubernetes_overview.pptx"
        prs = Presentation()
        s = prs.slides.add_slide(prs.slide_layouts[6])
        tb = s.shapes.add_textbox(0, 0, 400, 200)
        tb.text_frame.add_paragraph().text = "Containerization with Docker containers, images, and Kubernetes cluster orchestration."
        prs.save(str(p1))

        # 2. PDF: Database Normalization
        p2 = cls.docs_dir / "database_normalization_guide.pdf"
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 72), "Relational Database Design: 1NF, 2NF, 3NF, and Boyce-Codd Normal Form BCNF decomposition.")
        doc.save(str(p2))
        doc.close()

        # 3. XLSX: Employee Salary
        p3 = cls.docs_dir / "employee_salary_q4.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Salaries"
        ws.append(["Name", "Department", "Salary", "Bonus"])
        ws.append(["Elena Rostova", "AI Research", "$160,000", "$25,000"])
        wb.save(str(p3))

        # 4. DOCX: Decision Trees
        p4 = cls.docs_dir / "decision_trees_classification.docx"
        d = Document()
        d.add_heading("Decision Trees and Random Forests", level=1)
        d.add_paragraph("Decision tree algorithms split features using information gain, Gini impurity, and entropy.")
        d.save(str(p4))

        # 5. PPTX: Neural Networks
        p5 = cls.docs_dir / "neural_network_architectures.pptx"
        prs2 = Presentation()
        s2 = prs2.slides.add_slide(prs2.slide_layouts[6])
        tb2 = s2.shapes.add_textbox(0, 0, 400, 200)
        tb2.text_frame.add_paragraph().text = "Deep Learning: Convolutional Neural Networks CNNs and Recurrent Transformers."
        prs2.save(str(p5))

        # 6. CSV: Budget
        p6 = cls.docs_dir / "financial_budget_2026.csv"
        p6.write_text("Quarter,Marketing,Engineering,Operations\nQ1,50000,120000,30000\nQ2,55000,130000,32000", encoding="utf-8")

        # 7. TXT: TCP vs UDP
        p7 = cls.docs_dir / "network_protocols_tcp_udp.txt"
        p7.write_text("Transmission Control Protocol TCP offers connection-oriented reliable streams. User Datagram Protocol UDP is connectionless.", encoding="utf-8")

        # 8. MD: Load Balancers
        p8 = cls.docs_dir / "microservices_load_balancer.md"
        p8.write_text("# System Design: Load Balancers\nReverse proxies, round-robin scheduling, and health checks for microservices.", encoding="utf-8")

        # 9. RTF: Quantum Computing (Filename-only test)
        p9 = cls.docs_dir / "quantum_computing_notes.rtf"
        p9.write_text(r"{\rtf1\ansi Qubits, superposition, and quantum entanglement principles.}", encoding="utf-8")

        # 10. TXT: Exact Keyword Error Code
        p10 = cls.docs_dir / "incident_postmortem_october.txt"
        p10.write_text("Root cause: Critical outage caused by ERR_DATABASE_CONNECTION_POOL_EXHAUSTED when traffic peaked.", encoding="utf-8")

        # Index all
        cls.indexer = LensIndexer()
        cls.indexer.db = cls.db
        cls.indexer.vector_store = cls.vector_store
        cls.indexer._run_indexing_pipeline([str(cls.docs_dir)])

        cls.search_engine = SearchEngine()
        cls.search_engine.db = cls.db
        cls.search_engine.vector_store = cls.vector_store

        cls.eval_queries = [
            ("find me the presentation about docker and kubernetes", "docker_kubernetes_overview.pptx"),
            ("document explaining third normal form and BCNF database normalization", "database_normalization_guide.pdf"),
            ("find the spreadsheet containing employee salary compensation details", "employee_salary_q4.xlsx"),
            ("machine learning guide on decision tree splitting and entropy", "decision_trees_classification.docx"),
            ("presentation discussing convolutional and recurrent neural networks", "neural_network_architectures.pptx"),
            ("department budget allocation and quarterly expense forecast spreadsheet", "financial_budget_2026.csv"),
            ("reliable transmission control protocol vs user datagram protocol", "network_protocols_tcp_udp.txt"),
            ("system design article covering reverse proxies and load balancing", "microservices_load_balancer.md"),
            ("quantum_computing_notes", "quantum_computing_notes.rtf"),
            ("ERR_DATABASE_CONNECTION_POOL_EXHAUSTED", "incident_postmortem_october.txt")
        ]

    @classmethod
    def tearDownClass(cls):
        try:
            cls.temp_dir.cleanup()
        except Exception:
            pass

    def test_run_retrieval_evaluation(self):
        top1_hits = 0
        top3_hits = 0
        total = len(self.eval_queries)

        print("\n--- RETRIEVAL EVALUATION RESULTS ---")
        for q, expected_file in self.eval_queries:
            res = self.search_engine.search(q, top_k=5)
            retrieved_files = [r.file_name for r in res.results]

            hit1 = (len(retrieved_files) > 0 and retrieved_files[0] == expected_file)
            hit3 = expected_file in retrieved_files[:3]

            if hit1:
                top1_hits += 1
            if hit3:
                top3_hits += 1

            rank = retrieved_files.index(expected_file) + 1 if expected_file in retrieved_files else "N/A"
            print(f"Query: '{q[:40]}...' | Expected: {expected_file} | Rank: {rank}")

        top1_rate = (top1_hits / total) * 100
        top3_rate = (top3_hits / total) * 100
        print(f"Top-1 Hit Rate: {top1_hits}/{total} ({top1_rate:.1f}%)")
        print(f"Top-3 Hit Rate: {top3_hits}/{total} ({top3_rate:.1f}%)")
        print("------------------------------------\n")

        self.assertGreaterEqual(top3_rate, 70.0)


if __name__ == "__main__":
    unittest.main()
