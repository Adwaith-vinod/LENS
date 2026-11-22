import unittest
from backend.extraction.models import ContentUnit, ExtractionResult
from backend.processing.chunker import chunk_document, format_source_label, split_text_into_sentences


class TestChunking(unittest.TestCase):
    def test_sentence_splitting(self):
        text = "Hello world! This is a test. Machine learning works well.\n\nNext paragraph here."
        sentences = split_text_into_sentences(text)
        self.assertEqual(len(sentences), 4)
        self.assertEqual(sentences[0], "Hello world!")
        self.assertEqual(sentences[1], "This is a test.")

    def test_chunk_document_preserves_source_and_metadata(self):
        units = [
            ContentUnit(
                unit_type="page",
                unit_number=4,
                text="Decision trees are versatile machine learning algorithms. They can perform both classification and regression tasks.",
                metadata={"page_index": 3}
            ),
            ContentUnit(
                unit_type="slide",
                unit_number=2,
                text="Gradient boosting combines multiple weak learners into a strong predictive ensemble model.",
                metadata={"has_images": False}
            )
        ]
        result = ExtractionResult(
            file_name="ml_guide.pdf",
            file_path="C:/docs/ml_guide.pdf",
            file_type=".pdf",
            category="documents",
            content_units=units
        )

        chunks = chunk_document(result, chunk_size=200, chunk_overlap=30)
        self.assertGreaterEqual(len(chunks), 2)
        
        # Check first chunk
        c1 = chunks[0]
        self.assertEqual(c1.file_name, "ml_guide.pdf")
        self.assertEqual(c1.unit_type, "page")
        self.assertEqual(c1.unit_number, 4)
        self.assertEqual(c1.source_info, "Page 4")
        self.assertIn("Decision trees", c1.chunk_text)

        # Check second chunk
        c2 = chunks[1]
        self.assertEqual(c2.unit_type, "slide")
        self.assertEqual(c2.unit_number, 2)
        self.assertEqual(c2.source_info, "Slide 2")
        self.assertIn("Gradient boosting", c2.chunk_text)

    def test_source_label_formatting(self):
        unit_sheet = ContentUnit(unit_type="sheet", unit_number=1, text="", metadata={"sheet_name": "Q3 Revenue"})
        self.assertEqual(format_source_label(unit_sheet), "Sheet: Q3 Revenue")

        unit_page = ContentUnit(unit_type="page", unit_number=7, text="")
        self.assertEqual(format_source_label(unit_page), "Page 7")


if __name__ == "__main__":
    unittest.main()
