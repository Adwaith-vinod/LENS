
import unittest
import tempfile

from pathlib import Path

from backend.discovery.scanner import (
    scan_directory,
    scan_directories,
    get_file_metadata
)


class TestLensScanner(unittest.TestCase):

    def setUp(self):
        """
        Create a temporary directory before every test.
        """

        self.temp_dir = tempfile.TemporaryDirectory()

        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        """
        Delete temporary test files after every test.
        """

        self.temp_dir.cleanup()

    def test_discovers_supported_files(self):

        pdf = self.root / "notes.pdf"
        image = self.root / "plant.jpg"

        pdf.write_text("PDF placeholder")
        image.write_text("Image placeholder")

        results = scan_directory(self.root)

        filenames = {
            file["file_name"]
            for file in results
        }

        self.assertEqual(
            filenames,
            {"notes.pdf", "plant.jpg"}
        )

    def test_discovers_nested_files(self):

        college = self.root / "College"
        college.mkdir()

        document = college / "database.docx"
        document.write_text("Document placeholder")

        results = scan_directory(self.root)

        self.assertEqual(len(results), 1)

        self.assertEqual(
            results[0]["file_name"],
            "database.docx"
        )

    def test_ignores_excluded_directories(self):

        excluded = self.root / "node_modules"
        excluded.mkdir()

        document = excluded / "dependency.pdf"
        document.write_text("Should not be indexed")

        results = scan_directory(self.root)

        self.assertEqual(len(results), 0)

    def test_ignores_unsupported_files(self):

        unsupported = self.root / "program.exe"
        unsupported.write_text("Unsupported")

        results = scan_directory(self.root)

        self.assertEqual(len(results), 0)

    def test_returns_correct_file_metadata(self):

        document = self.root / "report.pdf"
        document.write_text("Sample report")

        metadata = get_file_metadata(document)

        self.assertEqual(
            metadata["file_name"],
            "report.pdf"
        )

        self.assertEqual(
            metadata["extension"],
            ".pdf"
        )

        self.assertEqual(
            metadata["category"],
            "documents"
        )

        self.assertEqual(
            metadata["file_size_bytes"],
            document.stat().st_size
        )

    def test_prevents_duplicate_files(self):

        nested = self.root / "College"
        nested.mkdir()

        document = nested / "notes.pdf"
        document.write_text("Notes")

        results = scan_directories([
            self.root,
            nested
        ])

        self.assertEqual(len(results), 1)

    def test_rejects_nonexistent_directory(self):

        missing = self.root / "does_not_exist"

        with self.assertRaises(FileNotFoundError):
            scan_directory(missing)


if __name__ == "__main__":
    unittest.main()
