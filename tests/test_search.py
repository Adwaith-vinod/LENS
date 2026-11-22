import unittest
import tempfile
from pathlib import Path
import openpyxl
from pptx import Presentation
import pymupdf

from backend.storage.db import DatabaseManager
from backend.storage.vector_store import PersistentVectorStore
from backend.indexing.indexer import LensIndexer
from backend.search.engine import SearchEngine


class TestSemanticSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp_dir.name)
        cls.docs_dir = cls.root / "documents"
        cls.docs_dir.mkdir()

        # 1. Create a PDF about Decision Trees and Machine Learning
        pdf_path = cls.docs_dir / "decision_trees.pdf"
        doc = pymupdf.open()
        p = doc.new_page()
        p.insert_text(
            (50, 72),
            "Chapter 4: Decision trees are non-parametric supervised learning methods used for classification and regression."
        )
        doc.save(str(pdf_path))
        doc.close()

        # 2. Create a Presentation about Neural Networks
        pptx_path = cls.docs_dir / "neural_networks.pptx"
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        tb = slide.shapes.add_textbox(0, 0, 400, 200)
        p = tb.text_frame.add_paragraph()
        p.text = "Deep Learning: Convolutional and Recurrent Neural Networks for Computer Vision and NLP."
        prs.save(str(pptx_path))

        # 3. Create a Spreadsheet about Employee Salaries
        xlsx_path = cls.docs_dir / "company_payroll.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Salaries"
        ws.append(["Name", "Department", "Salary"])
        ws.append(["Sarah Connor", "Security", "$120,000"])
        ws.append(["John Doe", "Engineering", "$135,000"])
        wb.save(str(xlsx_path))

        # Index the directory
        cls.db = DatabaseManager(cls.root / "lens_test.db")
        cls.vector_store = PersistentVectorStore(cls.root / "lens_test.index", dimension=384)
        cls.indexer = LensIndexer()
        cls.indexer.db = cls.db
        cls.indexer.vector_store = cls.vector_store
        cls.indexer._run_indexing_pipeline([str(cls.docs_dir)])

        cls.search_engine = SearchEngine()
        cls.search_engine.db = cls.db
        cls.search_engine.vector_store = cls.vector_store

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_search_decision_trees(self):
        query = "Find the document containing information about decision trees."
        response = self.search_engine.search(query, top_k=5)
        self.assertGreater(response.total_results, 0)
        top_result = response.results[0]
        self.assertEqual(top_result.file_name, "decision_trees.pdf")
        self.assertIn("Page 1", top_result.primary_source)
        self.assertIn("Decision trees", top_result.primary_snippet)
        self.assertGreater(top_result.relevance_score, 0.4)

    def test_search_neural_networks(self):
        query = "Find the presentation discussing neural networks."
        response = self.search_engine.search(query, top_k=5)
        self.assertGreater(response.total_results, 0)
        matching_names = [r.file_name for r in response.results]
        self.assertIn("neural_networks.pptx", matching_names)

    def test_search_employee_salaries(self):
        query = "Find the spreadsheet containing employee salary details."
        response = self.search_engine.search(query, top_k=5)
        self.assertGreater(response.total_results, 0)
        matching_names = [r.file_name for r in response.results]
        self.assertIn("company_payroll.xlsx", matching_names)


if __name__ == "__main__":
    unittest.main()
