import unittest
import tempfile
import json
from pathlib import Path

import pymupdf
from docx import Document
from pptx import Presentation
import openpyxl

from backend.extraction.unified import extract_file_content


class TestExtraction(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_extract_txt_and_markdown(self):
        txt_file = self.root / "sample.txt"
        txt_file.write_text("Hello LENS file discovery.\nMachine learning is fascinating.", encoding="utf-8")
        res = extract_file_content(str(txt_file))
        self.assertTrue(res.success)
        self.assertEqual(len(res.content_units), 1)
        self.assertIn("Machine learning", res.total_text)

        md_file = self.root / "sample.md"
        md_file.write_text("# Title\n\nDeep neural networks and transformers.", encoding="utf-8")
        res_md = extract_file_content(str(md_file))
        self.assertTrue(res_md.success)
        self.assertIn("Deep neural networks", res_md.total_text)

    def test_extract_pdf_pages(self):
        pdf_path = self.root / "multipage.pdf"
        doc = pymupdf.open()
        p1 = doc.new_page()
        p1.insert_text((50, 72), "Page 1: Introduction to system design and load balancing.")
        p2 = doc.new_page()
        p2.insert_text((50, 72), "Page 2: Database sharding and replication.")
        doc.save(str(pdf_path))
        doc.close()

        res = extract_file_content(str(pdf_path))
        self.assertTrue(res.success)
        self.assertEqual(len(res.content_units), 2)
        self.assertEqual(res.content_units[0].unit_number, 1)
        self.assertIn("system design", res.content_units[0].text)
        self.assertEqual(res.content_units[1].unit_number, 2)
        self.assertIn("Database sharding", res.content_units[1].text)

    def test_extract_docx(self):
        docx_path = self.root / "report.docx"
        doc = Document()
        doc.add_heading("Architecture Overview", level=1)
        doc.add_paragraph("LENS utilizes FAISS vector index with SQLite metadata storage.")
        table = doc.add_table(rows=1, cols=2)
        table.rows[0].cells[0].text = "Component"
        table.rows[0].cells[1].text = "Technology"
        doc.save(str(docx_path))

        res = extract_file_content(str(docx_path))
        self.assertTrue(res.success)
        self.assertIn("Architecture Overview", res.total_text)
        self.assertIn("FAISS vector index", res.total_text)
        self.assertIn("Component | Technology", res.total_text)

    def test_extract_pptx(self):
        pptx_path = self.root / "presentation.pptx"
        prs = Presentation()
        blank_slide_layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(blank_slide_layout)
        txBox = slide.shapes.add_textbox(0, 0, 400, 200)
        tf = txBox.text_frame
        p = tf.add_paragraph()
        p.text = "Convolutional Neural Networks for Image Recognition"
        prs.save(str(pptx_path))

        res = extract_file_content(str(pptx_path))
        self.assertTrue(res.success)
        self.assertEqual(len(res.content_units), 1)
        self.assertEqual(res.content_units[0].unit_type, "slide")
        self.assertEqual(res.content_units[0].unit_number, 1)
        self.assertIn("Convolutional Neural Networks", res.content_units[0].text)

    def test_extract_xlsx(self):
        xlsx_path = self.root / "salaries.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "EmployeeSalaries"
        ws.append(["Employee", "Role", "Salary"])
        ws.append(["Alice Smith", "ML Engineer", "$140,000"])
        ws.append(["Bob Jones", "Backend Dev", "$120,000"])
        wb.save(str(xlsx_path))

        res = extract_file_content(str(xlsx_path))
        self.assertTrue(res.success)
        self.assertEqual(len(res.content_units), 1)
        self.assertEqual(res.content_units[0].unit_type, "sheet")
        self.assertIn("EmployeeSalaries", res.content_units[0].text)
        self.assertIn("Alice Smith", res.content_units[0].text)

    def test_extract_json(self):
        json_path = self.root / "config.json"
        data = {"app": "LENS", "features": ["vector_search", "fastapi"], "version": 1}
        json_path.write_text(json.dumps(data), encoding="utf-8")

        res = extract_file_content(str(json_path))
        self.assertTrue(res.success)
        self.assertIn("vector_search", res.total_text)


if __name__ == "__main__":
    unittest.main()
