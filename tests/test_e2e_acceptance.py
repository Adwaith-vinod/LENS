import os
import unittest
import tempfile
import pymupdf
import openpyxl
from pptx import Presentation
from pathlib import Path

from backend.storage.db import DatabaseManager
from backend.storage.vector_store import PersistentVectorStore
from backend.indexing.indexer import LensIndexer
from backend.search.engine import SearchEngine
from backend.services.file_service import FileService


class TestEndToEndAcceptance(unittest.TestCase):
    """
    Validates Section 19 Final Acceptance Criteria:
    - Step 1: Launch LENS
    - Step 2: Discover accessible supported files
    - Step 3: Extract multiformat content
    - Step 4: Generate and persist embeddings
    - Step 5-7: Query 'Find the document containing information about decision trees' & verify citations
    - Step 8-9: Verify Open File resolution
    - Step 10-11: Restart LENS and verify persistence without re-embedding unchanged files
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temp_dir.name)
        self.data_dir = self.root / "data"
        self.data_dir.mkdir()
        self.docs_dir = self.root / "documents"
        self.docs_dir.mkdir()

        # Database and Vector paths
        self.db_path = self.data_dir / "lens.db"
        self.index_path = self.data_dir / "lens_text.index"

        # Create Synthetic Files
        # 1. Decision Trees PDF
        self.dt_pdf = self.docs_dir / "decision_trees_ml.pdf"
        doc = pymupdf.open()
        p = doc.new_page()
        p.insert_text(
            (50, 72),
            "Chapter 3: Decision trees are powerful machine learning models used for splitting datasets based on information gain and Gini impurity."
        )
        doc.save(str(self.dt_pdf))
        doc.close()

        # 2. Database Normalization Document (TXT)
        self.db_txt = self.docs_dir / "database_design.txt"
        self.db_txt.write_text(
            "Database normalization reduces data redundancy and improves data integrity through 1NF, 2NF, 3NF, and BCNF.",
            encoding="utf-8"
        )

        # 3. Employee Payroll Spreadsheet (XLSX)
        self.payroll_xlsx = self.docs_dir / "payroll_2026.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Q1_Salaries"
        ws.append(["EmpID", "Full Name", "Title", "Salary"])
        ws.append(["E001", "Dr. Jane Smith", "Chief AI Scientist", "$210,000"])
        wb.save(str(self.payroll_xlsx))

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_full_acceptance_workflow(self):
        # STEP 1 & 2: Initialize system components
        db = DatabaseManager(self.db_path)
        vector_store = PersistentVectorStore(self.index_path, dimension=384)
        indexer = LensIndexer()
        indexer.db = db
        indexer.vector_store = vector_store

        # STEP 3 & 4: Index discovered files & persist
        indexer._run_indexing_pipeline([str(self.docs_dir)])

        stats = db.get_statistics()
        self.assertEqual(stats["total_files"], 3)
        self.assertEqual(stats["indexed_files"], 3)
        self.assertGreater(vector_store.ntotal, 0)

        # STEP 5, 6, 7: Semantic retrieval with exact user query
        search_engine = SearchEngine()
        search_engine.db = db
        search_engine.vector_store = vector_store

        query = "Find the document containing information about decision trees."
        response = search_engine.search(query, top_k=5)

        self.assertGreater(response.total_results, 0)
        top = response.results[0]
        self.assertEqual(top.file_name, "decision_trees_ml.pdf")
        self.assertIn("Page 1", top.primary_source)
        self.assertIn("Decision trees", top.primary_snippet)
        self.assertGreater(top.relevance_score, 0.4)

        # STEP 8 & 9: Verify Open File resolution
        file_service = FileService()
        file_service.db = db
        resolved_path = file_service._resolve_path(top.file_id)
        self.assertEqual(os.path.normcase(resolved_path), os.path.normcase(str(self.dt_pdf)))
        self.assertTrue(Path(resolved_path).exists())

        # STEP 10: Simulate closing and restarting LENS
        # Instantiate brand-new DatabaseManager and PersistentVectorStore from disk
        db_restarted = DatabaseManager(self.db_path)
        vector_store_restarted = PersistentVectorStore(self.index_path, dimension=384)

        self.assertEqual(vector_store_restarted.ntotal, vector_store.ntotal)
        restarted_stats = db_restarted.get_statistics()
        self.assertEqual(restarted_stats["indexed_files"], 3)

        # STEP 11: Re-running indexer on unchanged files does not re-extract or duplicate
        indexer_restarted = LensIndexer()
        indexer_restarted.db = db_restarted
        indexer_restarted.vector_store = vector_store_restarted

        indexer_restarted._run_indexing_pipeline([str(self.docs_dir)])

        # Total vectors and files must remain unchanged (incremental deduplication verified)
        self.assertEqual(vector_store_restarted.ntotal, vector_store.ntotal)
        self.assertEqual(db_restarted.get_statistics()["total_files"], 3)


if __name__ == "__main__":
    unittest.main()
