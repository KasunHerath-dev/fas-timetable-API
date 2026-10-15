"""Unit tests for TimetableDownloader and manifest generation."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock
import pymupdf

from src.downloader import TimetableDownloader, compute_sha256
from src.models import TimetableCandidate, ManifestEntry
from datetime import datetime


class TestManifestAndDownloader(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.downloads_dir = Path(self.temp_dir.name) / "downloads"
        self.manifest_path = Path(self.temp_dir.name) / "metadata" / "manifest.json"
        self.downloader = TimetableDownloader(
            downloads_dir=self.downloads_dir,
            manifest_path=self.manifest_path,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_sample_pdf_bytes(self, content="Test PDF"):
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 100), content)
        data = doc.tobytes()
        doc.close()
        return data

    def test_compute_sha256(self):
        data = b"Hello FAS Timetables"
        h = compute_sha256(data)
        self.assertEqual(len(h), 64)

    def test_download_and_save_success(self):
        pdf_bytes = self._create_sample_pdf_bytes("Level 1 timetable test")
        candidate = TimetableCandidate(
            level=1,
            academic_year="2024/2025",
            academic_year_start=2024,
            semester="Semester I",
            semester_num=1,
            revision="Revised 02",
            revision_rank=2,
            pdf_url="https://fas.wyb.ac.lk/uploads/Level-1.pdf",
            notice_url="https://fas.wyb.ac.lk/notice-1/",
            notice_title="Notice 1",
            publication_date="2026-10-05",
            publication_datetime=datetime(2026, 10, 5),
            pdf_bytes=pdf_bytes,
            is_valid=True,
        )

        entry = self.downloader.download_and_save(candidate)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.level, 1)
        self.assertEqual(entry.publication_date, "2026-10-05")
        self.assertEqual(entry.file_size, len(pdf_bytes))
        self.assertEqual(entry.sha256, compute_sha256(pdf_bytes))

        # Check saved file on disk
        saved_file = self.downloads_dir / "level-1_2026-10-05.pdf"
        self.assertTrue(saved_file.exists())
        self.assertEqual(saved_file.read_bytes(), pdf_bytes)

    def test_update_manifest(self):
        pdf_bytes = self._create_sample_pdf_bytes("Manifest Level 2")
        entry = ManifestEntry(
            level=2,
            source_pdf_url="https://fas.wyb.ac.lk/uploads/Level-2.pdf",
            notice_url="https://fas.wyb.ac.lk/notice-2/",
            notice_title="Notice 2",
            publication_date="2026-09-10",
            academic_year="2024/2025",
            semester="Semester I",
            revision="Revised",
            download_timestamp="2026-10-15T12:00:00+00:00",
            local_path=str(self.downloads_dir / "level-2_2026-09-10.pdf"),
            file_size=len(pdf_bytes),
            sha256=compute_sha256(pdf_bytes),
        )

        ok = self.downloader.update_manifest(
            {2: entry},
            target_academic_year="2024/2025",
            target_semester="Semester I",
        )
        self.assertTrue(ok)
        self.assertTrue(self.manifest_path.exists())

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["target_academic_year"], "2024/2025")
        self.assertEqual(data["target_semester"], "Semester I")
        self.assertIn("2", data["levels"])
        self.assertEqual(data["levels"]["2"]["sha256"], compute_sha256(pdf_bytes))
        self.assertEqual(data["levels"]["2"]["local_path"], str(self.downloads_dir / "level-2_2026-09-10.pdf"))


if __name__ == "__main__":
    unittest.main()
