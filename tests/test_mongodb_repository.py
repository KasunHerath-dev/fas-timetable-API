"""Unit tests for MongoDB repository integration."""

import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.models import ManifestEntry
from src.parser_models import ParsedTimetable, TimetableSession, ValidationStatus
from src.mongodb_repository import (
    MongoTimetableRepository,
    MongoRepositoryError,
)
from src.cli import run, run_sync_parsed_to_mongodb


class FakeCollection:
    """A fake MongoDB collection for unit testing without a live server."""

    def __init__(self):
        self.docs = []
        self.indexes = []

    def create_index(self, keys, unique=False, name=""):
        self.indexes.append({"keys": keys, "unique": unique, "name": name})
        return name or "idx_test"

    def _matches(self, doc, filter_query):
        for k, v in filter_query.items():
            if isinstance(v, dict) and "$ne" in v:
                if doc.get(k) == v["$ne"]:
                    return False
            elif doc.get(k) != v:
                return False
        return True

    def find_one(self, filter_query, *args, **kwargs):
        for doc in self.docs:
            if self._matches(doc, filter_query):
                return dict(doc)
        return None

    def find(self, filter_query=None, *args, **kwargs):
        if not filter_query:
            return [dict(d) for d in self.docs]
        return [dict(d) for d in self.docs if self._matches(d, filter_query)]

    def delete_many(self, filter_query, *args, **kwargs):
        initial_len = len(self.docs)
        self.docs = [d for d in self.docs if not self._matches(d, filter_query)]
        mock_res = MagicMock()
        mock_res.deleted_count = initial_len - len(self.docs)
        return mock_res

    def update_one(self, filter_query, update_spec, upsert=False, *args, **kwargs):
        set_fields = update_spec.get("$set", {})
        existing = self.find_one(filter_query)

        mock_res = MagicMock()
        if existing:
            for doc in self.docs:
                if self._matches(doc, filter_query):
                    doc.update(set_fields)
                    break
            mock_res.upserted_id = None
            mock_res.modified_count = 1
        elif upsert:
            new_doc = dict(set_fields)
            new_doc.update({k: v for k, v in filter_query.items() if not isinstance(v, dict)})
            new_doc["_id"] = len(self.docs) + 1
            self.docs.append(new_doc)
            mock_res.upserted_id = new_doc["_id"]
            mock_res.modified_count = 0
        else:
            mock_res.upserted_id = None
            mock_res.modified_count = 0

        return mock_res


class TestMongoTimetableRepository(unittest.TestCase):

    def setUp(self):
        self.fake_collection = FakeCollection()
        self.fake_sessions_col = FakeCollection()
        self.fake_db = MagicMock()
        self.fake_db.__getitem__.side_effect = lambda name: (
            self.fake_sessions_col if name == "timetable_sessions" else self.fake_collection
        )
        self.fake_client = MagicMock()
        self.fake_client.__getitem__.return_value = self.fake_db

        self.repo = MongoTimetableRepository(
            uri="mongodb://localhost:27017",
            database_name="test_db",
            collection_name="timetables",
            sessions_collection_name="timetable_sessions",
            client=self.fake_client,
        )

    def _sample_entry(
        self,
        level: int = 1,
        year: str = "2024/2025",
        sem: str = "Semester I",
        rev: str = "Revised 02",
        sha256: str = "hash1234567890",
    ) -> ManifestEntry:
        return ManifestEntry(
            level=level,
            source_pdf_url="https://fas.wyb.ac.lk/uploads/Level-1.pdf",
            notice_url="https://fas.wyb.ac.lk/notice-1/",
            notice_title="Revised Notice Level 1",
            publication_date="2026-10-05",
            academic_year=year,
            semester=sem,
            revision=rev,
            download_timestamp="2026-10-15T12:00:00+05:30",
            local_path="downloads/level-1_2026-10-05.pdf",
            file_size=675037,
            sha256=sha256,
        )

    def test_ensure_unique_compound_index(self):
        idx_names = self.repo.ensure_indexes()
        self.assertEqual(len(self.fake_collection.indexes), 1)
        idx = self.fake_collection.indexes[0]
        self.assertTrue(idx["unique"])
        self.assertEqual(
            idx["keys"],
            [("level", 1), ("academicYear", 1), ("semester", 1)],
        )

        # Check sessions indexes
        self.assertEqual(len(self.fake_sessions_col.indexes), 3)
        slot_idx = self.fake_sessions_col.indexes[0]
        self.assertTrue(slot_idx["unique"])
        self.assertEqual(slot_idx["name"], "idx_session_unique_slot")

    def test_upsert_creates_record(self):
        entry = self._sample_entry(level=1)
        res = self.repo.sync_timetable_entry(entry)
        self.assertEqual(res["action"], "upserted")
        self.assertEqual(len(self.fake_collection.docs), 1)

        saved = self.fake_collection.docs[0]
        self.assertEqual(saved["level"], 1)
        self.assertEqual(saved["academicYear"], "2024/2025")
        self.assertEqual(saved["semester"], "Semester I")
        self.assertEqual(saved["revision"], "Revised 02")
        self.assertEqual(saved["sha256"], "hash1234567890")

    def test_repeated_sync_no_duplicates_and_hash_avoids_write(self):
        entry = self._sample_entry(level=1, sha256="samehash123")
        res1 = self.repo.sync_timetable_entry(entry)
        self.assertEqual(res1["action"], "upserted")
        self.assertEqual(len(self.fake_collection.docs), 1)

        # Repeated run with exact same SHA-256 hash
        res2 = self.repo.sync_timetable_entry(entry)
        self.assertEqual(res2["action"], "skipped")
        self.assertEqual(res2["reason"], "sha256_match")
        self.assertEqual(len(self.fake_collection.docs), 1)

    def test_new_revision_updates_correct_academic_period(self):
        entry_old = self._sample_entry(level=1, rev="Revised 01", sha256="oldhash")
        self.repo.sync_timetable_entry(entry_old)
        self.assertEqual(self.fake_collection.docs[0]["revision"], "Revised 01")

        # New revision for the same academic period
        entry_new = self._sample_entry(level=1, rev="Revised 02", sha256="newhash")
        res = self.repo.sync_timetable_entry(entry_new)
        self.assertEqual(res["action"], "updated")
        self.assertEqual(len(self.fake_collection.docs), 1)
        self.assertEqual(self.fake_collection.docs[0]["revision"], "Revised 02")
        self.assertEqual(self.fake_collection.docs[0]["sha256"], "newhash")

    def test_other_levels_remain_untouched(self):
        entry_l1 = self._sample_entry(level=1, sha256="l1hash")
        entry_l2 = self._sample_entry(level=2, sha256="l2hash")
        self.repo.sync_timetable_entry(entry_l1)
        self.repo.sync_timetable_entry(entry_l2)
        self.assertEqual(len(self.fake_collection.docs), 2)

        # Update only Level 1
        entry_l1_rev = self._sample_entry(level=1, rev="Revised 03", sha256="l1newhash")
        self.repo.sync_timetable_entry(entry_l1_rev)

        # Level 2 remains untouched
        l2_doc = self.fake_collection.find_one({"level": 2})
        self.assertIsNotNone(l2_doc)
        self.assertEqual(l2_doc["sha256"], "l2hash")
        self.assertEqual(l2_doc["revision"], "Revised 02")

    def test_missing_environment_configuration_handled_safely(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as ctx:
                MongoTimetableRepository(uri=None, client=None)
            self.assertIn("MONGODB_URI", str(ctx.exception))

    def test_skip_mongodb_option_works_without_credentials(self):
        temp_dir = tempfile.TemporaryDirectory()
        dl_dir = Path(temp_dir.name) / "downloads"
        man_path = Path(temp_dir.name) / "manifest.json"

        # Mock scraper to return dummy notice and PDF
        with patch("src.cli.TimetableScraper") as mock_scraper_cls, \
             patch("src.cli.inspect_pdf_bytes") as mock_inspect, \
             patch.dict(os.environ, {}, clear=True):

            # Scraper returns no notices -> cleanly returns 1
            mock_scraper = MagicMock()
            mock_scraper.discover_notices.return_value = []
            mock_scraper_cls.return_value = mock_scraper

            exit_code = run(
                downloads_dir=dl_dir,
                manifest_path=man_path,
                skip_mongodb=True,
            )
            # Returns 1 because no notices, but DID NOT crash on missing MONGODB_URI
            self.assertEqual(exit_code, 1)

        temp_dir.cleanup()

    def test_dry_run_never_writes_to_mongodb(self):
        mock_repo = MagicMock()
        temp_dir = tempfile.TemporaryDirectory()

        with patch("src.cli.TimetableScraper") as mock_scraper_cls:
            mock_scraper = MagicMock()
            mock_scraper.discover_notices.return_value = []
            mock_scraper_cls.return_value = mock_scraper

            exit_code = run(
                dry_run=True,
                mongo_repo=mock_repo,
            )
            mock_repo.sync_all.assert_not_called()
            mock_repo.sync_timetable_entry.assert_not_called()
            self.assertEqual(exit_code, 1)

        temp_dir.cleanup()

    def test_mongodb_failure_preserves_local_files_and_manifest(self):
        temp_dir = tempfile.TemporaryDirectory()
        dl_dir = Path(temp_dir.name) / "downloads"
        dl_dir.mkdir(parents=True)
        man_path = Path(temp_dir.name) / "manifest.json"

        # Create a mock repo whose sync_all raises an error
        mock_repo = MagicMock()
        mock_repo.sync_all.side_effect = MongoRepositoryError("Simulated network timeout")

        with patch("src.cli.TimetableScraper") as mock_scraper_cls, \
             patch("src.cli.TimetableDownloader.fetch_pdf_data", return_value=b"%PDF-sample"), \
             patch("src.cli.TimetableDownloader.download_and_save") as mock_save, \
             patch("src.cli.TimetableDownloader.update_manifest") as mock_update_man, \
             patch("src.cli.inspect_pdf_bytes") as mock_inspect:

            notice_mock = MagicMock()
            notice_mock.title = "Notice 1"
            notice_mock.publication_date = "2026-10-05"
            notice_mock.publication_datetime = datetime(2026, 10, 5)
            notice_mock.pdf_links = [MagicMock(url="https://fas.wyb.ac.lk/l1.pdf", text="Level 01")]

            mock_scraper = MagicMock()
            mock_scraper.discover_notices.return_value = [notice_mock]
            mock_scraper_cls.return_value = mock_scraper

            mock_inspect.return_value = (
                True,
                {
                    "level": 1,
                    "academic_year": "2024/2025",
                    "academic_year_start": 2024,
                    "semester": "Semester I",
                    "semester_num": 1,
                    "revision": "Revised 02",
                    "revision_rank": 2,
                },
                None,
            )

            mock_save.return_value = self._sample_entry(level=1)
            mock_update_man.return_value = True

            exit_code = run(
                downloads_dir=dl_dir,
                manifest_path=man_path,
                target_levels=(1,),
                mongo_repo=mock_repo,
            )
            # Must return non-zero exit code due to Mongo sync error
            self.assertEqual(exit_code, 2)
            # Verify download_and_save and update_manifest WERE called before the failure
            mock_save.assert_called_once()
            mock_update_man.assert_called_once()

        temp_dir.cleanup()

    def _sample_parsed_timetable(
        self,
        level: int = 1,
        year: str = "2024/2025",
        semester: str = "Semester I",
        source_hash: str = "hash_v1",
        num_sessions: int = 2,
    ) -> ParsedTimetable:
        sessions = []
        for i in range(num_sessions):
            sess = TimetableSession(
                day="Monday",
                start_time=f"0{8+i}:30",
                end_time=f"0{9+i}:30",
                subject_code=f"CMIS 11{i+1}3",
                session_type="Lecture",
                group=None,
                location=f"LR-{i+1}",
                raw_cell_text=f"CMIS 11{i+1}3 (L)\nLR-{i+1}",
                validation_status=ValidationStatus.VALID,
                warnings=[],
            )
            sessions.append(sess)

        return ParsedTimetable(
            level=level,
            academic_year=year,
            semester=semester,
            revision="Revised 01",
            source_pdf=f"downloads/level-{level}.pdf",
            source_sha256=source_hash,
            extraction_timestamp="2026-10-15T12:00:00+05:30",
            total_sessions=len(sessions),
            valid_sessions=len(sessions),
            records_needing_review=0,
            sessions=sessions,
            warnings=[],
        )

    def test_sync_parsed_timetable_sessions_upsert_and_skip(self):
        parsed = self._sample_parsed_timetable(level=1, source_hash="hash_v1", num_sessions=2)
        res = self.repo.sync_parsed_timetable_sessions(parsed)

        self.assertEqual(res["level"], 1)
        self.assertEqual(res["counts"]["upserted"], 2)
        self.assertEqual(len(self.fake_sessions_col.docs), 2)

        # Repeated sync with same content -> skipped (no unnecessary writes)
        res2 = self.repo.sync_parsed_timetable_sessions(parsed)
        self.assertEqual(res2["counts"]["skipped"], 2)
        self.assertEqual(res2["counts"]["upserted"], 0)
        self.assertEqual(len(self.fake_sessions_col.docs), 2)

    def test_sync_parsed_timetable_sessions_prunes_stale_when_hash_changes(self):
        parsed_v1 = self._sample_parsed_timetable(level=1, source_hash="hash_v1", num_sessions=2)
        self.repo.sync_parsed_timetable_sessions(parsed_v1)
        self.assertEqual(len(self.fake_sessions_col.docs), 2)

        # New timetable revision with only 1 session and different hash
        parsed_v2 = self._sample_parsed_timetable(level=1, source_hash="hash_v2", num_sessions=1)
        res_v2 = self.repo.sync_parsed_timetable_sessions(parsed_v2)

        self.assertEqual(res_v2["counts"]["updated"], 1)
        self.assertEqual(res_v2["counts"]["stale_deleted"], 1)  # the removed session was pruned
        # Now exactly 1 session exists
        self.assertEqual(len(self.fake_sessions_col.docs), 1)
        self.assertEqual(self.fake_sessions_col.docs[0]["sourcePdfHash"], "hash_v2")

    def test_sync_parsed_preserves_needs_review_records(self):
        parsed = self._sample_parsed_timetable(level=4, source_hash="hash_l4", num_sessions=1)
        review_session = TimetableSession(
            day="Monday",
            start_time="13:30",
            end_time="14:30",
            subject_code="ELTN 4+92",
            session_type="Seminar",
            group=None,
            location="Seminar Room",
            raw_cell_text="ELTN 4+92\nSeminar Room",
            validation_status=ValidationStatus.NEEDS_REVIEW,
            warnings=["Unusual character '+' in subject code"],
        )
        parsed.sessions.append(review_session)
        parsed.total_sessions = 2
        parsed.records_needing_review = 1

        self.repo.sync_parsed_timetable_sessions(parsed)
        docs = self.fake_sessions_col.docs
        self.assertEqual(len(docs), 2)

        # Find the review document
        rev_doc = [d for d in docs if d["subjectCode"] == "ELTN 4+92"][0]
        self.assertEqual(rev_doc["validationStatus"], "NEEDS_REVIEW")
        self.assertIn("Unusual character '+' in subject code", rev_doc["warnings"])
        self.assertEqual(rev_doc["rawCellText"], "ELTN 4+92\nSeminar Room")

    def test_sync_parsed_timetable_sessions_isolates_levels(self):
        parsed_l1 = self._sample_parsed_timetable(level=1, source_hash="l1_hash", num_sessions=2)
        parsed_l2 = self._sample_parsed_timetable(level=2, source_hash="l2_hash", num_sessions=3)

        self.repo.sync_parsed_timetable_sessions(parsed_l1)
        self.repo.sync_parsed_timetable_sessions(parsed_l2)
        self.assertEqual(len(self.fake_sessions_col.docs), 5)

        # Update level 1 with a new hash
        parsed_l1_v2 = self._sample_parsed_timetable(level=1, source_hash="l1_hash_v2", num_sessions=1)
        self.repo.sync_parsed_timetable_sessions(parsed_l1_v2)

        # Level 2 sessions should be completely untouched (still 3)
        l2_docs = [d for d in self.fake_sessions_col.docs if d["level"] == 2]
        self.assertEqual(len(l2_docs), 3)

        # Level 1 sessions should now be 1
        l1_docs = [d for d in self.fake_sessions_col.docs if d["level"] == 1]
        self.assertEqual(len(l1_docs), 1)

    def test_dry_run_sync_parsed_to_mongodb(self):
        mock_repo = MagicMock()
        # Use existing data/parsed directory
        exit_code = run_sync_parsed_to_mongodb(
            parsed_dir=Path("data/parsed"),
            dry_run=True,
            mongo_repo=mock_repo,
        )
        # Must return 0 and make zero writes
        mock_repo.sync_all_parsed_sessions.assert_not_called()
        mock_repo.sync_parsed_timetable_sessions.assert_not_called()
        self.assertEqual(exit_code, 0)

    def test_sync_parsed_handles_corrupt_json_safely(self):
        temp_dir = tempfile.TemporaryDirectory()
        corrupt_dir = Path(temp_dir.name)
        corrupt_file = corrupt_dir / "level-1.json"
        corrupt_file.write_text("NOT_VALID_JSON", encoding="utf-8")

        mock_repo = MagicMock()
        exit_code = run_sync_parsed_to_mongodb(
            parsed_dir=corrupt_dir,
            dry_run=False,
            mongo_repo=mock_repo,
        )
        # Must return non-zero exit code (1) and not call database
        self.assertEqual(exit_code, 1)
        mock_repo.sync_all_parsed_sessions.assert_not_called()

        temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()

