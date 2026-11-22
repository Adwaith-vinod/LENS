import unittest
import tempfile
import os
from pathlib import Path
from pptx import Presentation

from backend.storage.db import DatabaseManager
from backend.storage.vector_store import PersistentVectorStore
from backend.discovery.scanner import scan_directory
from backend.extraction.unified import extract_file_content
from backend.processing.chunker import chunk_document
from backend.embeddings.engine import get_embedding_engine
from backend.indexing.indexer import LensIndexer
from backend.search.engine import SearchEngine


class TestPptxRetrievalRegression(unittest.TestCase):
    """
    Regression test suite for PowerPoint discovery, extraction, chunking,
    embedding, persistence, and semantic retrieval with intent prioritization.
    """

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.root = Path(cls.temp_dir.name)
        cls.docs_dir = cls.root / "docs"
        cls.docs_dir.mkdir()

        # Database and Vector store paths
        cls.db_path = cls.root / "test_lens.db"
        cls.index_path = cls.root / "test_lens.index"

        # 1. Create a synthetic PowerPoint presentation about Docker and Kubernetes
        cls.pptx_path = cls.docs_dir / "docker_and_kubernetes_guide.pptx"
        prs = Presentation()

        # Slide 1: Introduction to Containerization
        slide1 = prs.slides.add_slide(prs.slide_layouts[6])
        tb1 = slide1.shapes.add_textbox(0, 0, 400, 200)
        p1 = tb1.text_frame.add_paragraph()
        p1.text = "Introduction to Containerization and Microservices Architecture."

        # Slide 2: Docker Images and Containers
        slide2 = prs.slides.add_slide(prs.slide_layouts[6])
        tb2 = slide2.shapes.add_textbox(0, 0, 400, 200)
        p2 = tb2.text_frame.add_paragraph()
        p2.text = "Docker Images, Docker Containers, Dockerfiles, and Docker Hub registries."

        # Slide 3: Kubernetes Pods and Deployments
        slide3 = prs.slides.add_slide(prs.slide_layouts[6])
        tb3 = slide3.shapes.add_textbox(0, 0, 400, 200)
        p3 = tb3.text_frame.add_paragraph()
        p3.text = "Kubernetes Pods, ReplicaSets, Deployments, Services, and Ingress controllers."

        # Slide 4: Container Orchestration & Scaling
        slide4 = prs.slides.add_slide(prs.slide_layouts[6])
        tb4 = slide4.shapes.add_textbox(0, 0, 400, 200)
        p4 = tb4.text_frame.add_paragraph()
        p4.text = "Container Orchestration and Autoscaling with Kubernetes and Docker Swarm."

        prs.save(str(cls.pptx_path))

        # 2. Create a competing document (Markdown) that mentions Docker casually
        cls.md_path = cls.docs_dir / "devops_notes.md"
        cls.md_path.write_text(
            "# General DevOps Notes\n\nWe briefly use Docker for testing local scripts.\n"
            "Main focus is CI/CD pipelines with GitHub Actions.",
            encoding="utf-8"
        )

        # 3. Setup Indexer & Search Engine
        cls.db = DatabaseManager(cls.db_path)
        cls.vector_store = PersistentVectorStore(cls.index_path, dimension=384)
        cls.indexer = LensIndexer()
        cls.indexer.db = cls.db
        cls.indexer.vector_store = cls.vector_store

        # Index the test folder
        cls.indexer._run_indexing_pipeline([str(cls.docs_dir)])

        cls.search_engine = SearchEngine()
        cls.search_engine.db = cls.db
        cls.search_engine.vector_store = cls.vector_store

    @classmethod
    def tearDownClass(cls):
        try:
            cls.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_scanner_discovers_pptx(self):
        discovered = scan_directory(self.docs_dir)
        names = {f["file_name"] for f in discovered}
        self.assertIn("docker_and_kubernetes_guide.pptx", names)

    def test_02_extractor_reads_all_slide_text(self):
        res = extract_file_content(str(self.pptx_path))
        self.assertTrue(res.success)
        self.assertEqual(len(res.content_units), 4)
        self.assertIn("Introduction to Containerization", res.total_text)
        self.assertIn("Docker Images", res.total_text)
        self.assertIn("Kubernetes Pods", res.total_text)
        self.assertIn("Container Orchestration", res.total_text)

    def test_03_slide_numbers_preserved(self):
        res = extract_file_content(str(self.pptx_path))
        slide_numbers = [u.unit_number for u in res.content_units]
        self.assertEqual(slide_numbers, [1, 2, 3, 4])
        self.assertEqual(res.content_units[2].unit_type, "slide")
        self.assertIn("Kubernetes Pods", res.content_units[2].text)

    def test_04_chunks_retain_metadata(self):
        res = extract_file_content(str(self.pptx_path))
        chunks = chunk_document(res)
        self.assertGreaterEqual(len(chunks), 4)
        for c in chunks:
            self.assertEqual(c.file_name, "docker_and_kubernetes_guide.pptx")
            self.assertEqual(c.unit_type, "slide")
            self.assertIn("Slide", c.source_info)

    def test_05_embeddings_generated_for_presentation(self):
        res = extract_file_content(str(self.pptx_path))
        chunks = chunk_document(res)
        engine = get_embedding_engine()
        vectors = engine.encode_texts([c.chunk_text for c in chunks])
        self.assertEqual(len(vectors), len(chunks))
        self.assertEqual(vectors.shape[1], 384)

    def test_06_presentation_vectors_in_faiss(self):
        self.assertGreater(self.vector_store.ntotal, 0)

    def test_07_metadata_maps_to_original_presentation(self):
        file_rec = self.db.get_file_by_path(str(self.pptx_path.resolve()))
        self.assertIsNotNone(file_rec)
        self.assertEqual(file_rec["file_name"], "docker_and_kubernetes_guide.pptx")
        self.assertEqual(file_rec["category"], "presentations")

    def test_08_query_retrieves_presentation(self):
        query = "find me the presentation file about docker and kubernetes"
        res = self.search_engine.search(query, top_k=5)
        self.assertGreater(res.total_results, 0)
        top = res.results[0]
        self.assertEqual(top.file_name, "docker_and_kubernetes_guide.pptx")
        self.assertEqual(top.category, "presentations")
        self.assertIn("Slide", top.primary_source)

    def test_09_explicit_presentation_query_prioritizes_presentation_over_doc(self):
        query = "find me the presentation about docker and kubernetes"
        res = self.search_engine.search(query, top_k=5)
        # Presentation must rank higher than devops_notes.md
        matching_files = [r.file_name for r in res.results]
        self.assertIn("docker_and_kubernetes_guide.pptx", matching_files)
        pptx_rank = matching_files.index("docker_and_kubernetes_guide.pptx")
        if "devops_notes.md" in matching_files:
            md_rank = matching_files.index("devops_notes.md")
            self.assertLess(pptx_rank, md_rank)

    def test_10_presentation_searchable_after_restarting(self):
        # Reload DB and FAISS from disk
        db_reloaded = DatabaseManager(self.db_path)
        vector_reloaded = PersistentVectorStore(self.index_path, dimension=384)

        searcher = SearchEngine()
        searcher.db = db_reloaded
        searcher.vector_store = vector_reloaded

        query = "find me the presentation file about docker and kubernetes"
        res = searcher.search(query, top_k=5)
        self.assertGreater(res.total_results, 0)
        self.assertEqual(res.results[0].file_name, "docker_and_kubernetes_guide.pptx")

    def test_11_category_filters(self):
        query = "docker"
        # Filter: presentations
        res_ppt = self.search_engine.search(query, category="presentations", top_k=5)
        self.assertTrue(all(r.category == "presentations" for r in res_ppt.results))
        self.assertIn("docker_and_kubernetes_guide.pptx", [r.file_name for r in res_ppt.results])

        # Filter: documents (should only find devops_notes.md)
        res_doc = self.search_engine.search(query, category="documents", top_k=5)
        self.assertTrue(all(r.category == "documents" for r in res_doc.results))
        self.assertNotIn("docker_and_kubernetes_guide.pptx", [r.file_name for r in res_doc.results])


if __name__ == "__main__":
    unittest.main()
