"""Unit tests for TimetableProductionWorker and validation logic."""

import hashlib
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.models import TimetableCandidate, ManifestEntry, Notice, PDFLinkInfo
from src.parser_models import ParsedTimetable, TimetableSession, ValidationStatus
from src.mongodb_repository import MongoTimetableRepository, MongoRepositoryError
from src.worker import (
    TimetableProductionWorker,
    validate_parsed_timetable,
    deduplicate_identical_sessions,
)


class FakeCollection:
    """In-memory MongoDB collection for testing."""

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
            new_doc["_id"] = f"doc_{len(self.docs) + 1}"
            self.docs.append(new_doc)
            mock_res.upserted_id = new_doc["_id"]
            mock_res.modified_count = 0
        else:
            mock_res.upserted_id = None
            mock_res.modified_count = 0

        return mock_res


class TestWorkerValidation(unittest.TestCase):
    """Test candidate timetable pre-sync validation rules."""

    def _create_sample_session(self, **overrides):
        defaults = {
            "day": "Monday",
            "start_time": "08:30",
            "end_time": "09:30",
            "subject_code": "CMIS 1113",
            "session_type": "Lecture",
            "group": None,
            "location": "LR- 07",
            "raw_cell_text": "CMIS 1113 (L)\nLR- 07",
            "validation_status": ValidationStatus.VALID,
            "warnings": [],
        }
        defaults.update(overrides)
        return TimetableSession(**defaults)

    def _create_sample_parsed(self, sessions=None, **overrides):
        if sessions is None:
            sessions = [self._create_sample_session()]
        defaults = {
            "level": 1,
            "academic_year": "2024/2025",
            "semester": "Semester I",
            "revision": "Revised 02",
            "source_pdf": "level-1_2026-10-05.pdf",
            "source_sha256": "a" * 64,
            "extraction_timestamp": "2026-10-16T00:00:00+00:00",
            "sessions": sessions,
            "warnings": [],
            "records_needing_review": 0,
            "total_sessions": len(sessions),
        }
        defaults.update(overrides)
        return ParsedTimetable(**defaults)

    def test_valid_parsed_timetable_passes(self):
        parsed = self._create_sample_parsed()
        is_valid, errors = validate_parsed_timetable(parsed)
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])

    def test_invalid_level_fails(self):
        parsed = self._create_sample_parsed(level=5)
        is_valid, errors = validate_parsed_timetable(parsed)
        self.assertFalse(is_valid)
        self.assertTrue(any("Invalid academic level" in e for e in errors))

    def test_empty_sessions_fails(self):
        parsed = self._create_sample_parsed(sessions=[])
        is_valid, errors = validate_parsed_timetable(parsed)
        self.assertFalse(is_valid)
        self.assertTrue(any("Insufficient session count" in e for e in errors))

    def test_invalid_day_fails(self):
        sess = self._create_sample_session(day="Saturday")
        parsed = self._create_sample_parsed(sessions=[sess])
        is_valid, errors = validate_parsed_timetable(parsed)
        self.assertFalse(is_valid)
        self.assertTrue(any("Invalid weekday" in e for e in errors))

    def test_invalid_time_range_fails(self):
        # Start time after end time
        sess = self._create_sample_session(start_time="10:30", end_time="09:30")
        parsed = self._create_sample_parsed(sessions=[sess])
        is_valid, errors = validate_parsed_timetable(parsed)
        self.assertFalse(is_valid)
        self.assertTrue(any("must precede end time" in e for e in errors))

    def test_zero_time_slot_fails(self):
        sess = self._create_sample_session(start_time="00:00", end_time="00:00")
        parsed = self._create_sample_parsed(sessions=[sess])
        is_valid, errors = validate_parsed_timetable(parsed)
        self.assertFalse(is_valid)
        self.assertTrue(any("Unresolved zero time slot" in e for e in errors))

    def test_missing_raw_cell_text_fails(self):
        sess = self._create_sample_session(raw_cell_text="")
        parsed = self._create_sample_parsed(sessions=[sess])
        is_valid, errors = validate_parsed_timetable(parsed)
        self.assertFalse(is_valid)
        self.assertTrue(any("Missing raw cell text" in e for e in errors))

    def test_conflicting_duplicate_slot_fails(self):
        sess1 = self._create_sample_session(day="Monday", start_time="08:30", end_time="09:30", location="LR-01")
        sess2 = self._create_sample_session(day="Monday", start_time="08:30", end_time="10:30", location="LR-02")
        parsed = self._create_sample_parsed(sessions=[sess1, sess2])
        is_valid, errors = validate_parsed_timetable(parsed)
        self.assertFalse(is_valid)
        self.assertTrue(any("Conflicting duplicate slot" in e for e in errors))

    def test_deduplicate_identical_sessions(self):
        sess1 = self._create_sample_session(location="LR-01")
        sess2 = self._create_sample_session(location="LR-01")
        unique, count = deduplicate_identical_sessions([sess1, sess2])
        self.assertEqual(count, 1)
        self.assertEqual(len(unique), 1)


class TestTimetableProductionWorker(unittest.TestCase):
    """Test suite for TimetableProductionWorker execution scenarios."""

    def setUp(self):
        self.fake_tt_col = FakeCollection()
        self.fake_sess_col = FakeCollection()
        self.fake_db = MagicMock()
        self.fake_db.__getitem__.side_effect = lambda name: (
            self.fake_sess_col if name == "timetable_sessions" else self.fake_tt_col
        )
        self.fake_client = MagicMock()
        self.fake_client.__getitem__.return_value = self.fake_db
        self.fake_client.admin.command.return_value = {"ok": 1}

        self.repo = MongoTimetableRepository(
            uri="mongodb://localhost:27017",
            database_name="test_db",
            collection_name="timetables",
            sessions_collection_name="timetable_sessions",
            client=self.fake_client,
        )

    def _create_mock_candidate(self, level=1, revision="Revised 01", sha_content=b"pdf_v1"):
        sha = hashlib.sha256(sha_content).hexdigest() if sha_content is not None else "dummy_hash"
        dt = datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc)
        return TimetableCandidate(
            level=level,
            academic_year="2024/2025",
            academic_year_start=2024,
            semester="Semester I",
            semester_num=1,
            revision=revision,
            revision_rank=1,
            pdf_url=f"https://fas.wyb.ac.lk/l{level}.pdf",
            notice_url=f"https://fas.wyb.ac.lk/notice-{level}/",
            notice_title=f"Notice Level {level}",
            publication_date="2026-10-05",
            publication_datetime=dt,
            pdf_bytes=sha_content,
            is_valid=True,
        )

    def _create_mock_parsed(self, level=1, revision="Revised 01", sha_content=b"pdf_v1"):
        sha = hashlib.sha256(sha_content).hexdigest()
        session = TimetableSession(
            day="Monday",
            start_time="08:30",
            end_time="09:30",
            subject_code=f"CMIS {level}113",
            session_type="Lecture",
            group=None,
            location="LR- 07",
            raw_cell_text=f"CMIS {level}113 (L)\nLR- 07",
            validation_status=ValidationStatus.VALID,
            warnings=[],
        )
        return ParsedTimetable(
            level=level,
            academic_year="2024/2025",
            semester="Semester I",
            revision=revision,
            source_pdf=f"level-{level}_2026-10-05.pdf",
            source_sha256=sha,
            extraction_timestamp="2026-10-16T00:00:00+00:00",
            sessions=[session],
            warnings=[],
            records_needing_review=0,
            total_sessions=1,
        )

    def test_no_changes_detected_no_database_writes(self):
        """Worker exits 0 without unnecessary writes when stored SHA-256 matches."""
        cand1 = self._create_mock_candidate(level=1, sha_content=b"content_1")
        cand_hash = hashlib.sha256(b"content_1").hexdigest()

        # Seed database with identical metadata
        self.fake_tt_col.docs.append({
            "level": 1,
            "academicYear": "2024/2025",
            "semester": "Semester I",
            "revision": "Revised 01",
            "sha256": cand_hash,
        })

        worker = TimetableProductionWorker(
            target_levels=(1,),
            mongo_repo=self.repo,
        )
        worker.discover_and_select_candidates = MagicMock(return_value=({1: cand1}, {}, (2024, 1, "2024/2025", "Semester I")))

        with patch("src.worker.TimetablePDFParser") as mock_parser_cls:
            exit_code = worker.run()

        self.assertEqual(exit_code, 0)
        # Ensure parser was never even called because no changes were detected
        mock_parser_cls.assert_not_called()
        # Verify no sessions were inserted or deleted
        self.assertEqual(len(self.fake_sess_col.docs), 0)

    def test_new_pdf_single_level_synchronization(self):
        """When a new PDF exists for Level 1, only Level 1 is parsed and synchronized."""
        cand1 = self._create_mock_candidate(level=1, sha_content=b"pdf_content_l1")
        cand2 = self._create_mock_candidate(level=2, sha_content=b"pdf_content_l2")
        l2_hash = hashlib.sha256(b"pdf_content_l2").hexdigest()

        # Seed database with Level 2 already up-to-date
        self.fake_tt_col.docs.append({
            "level": 2,
            "academicYear": "2024/2025",
            "semester": "Semester I",
            "revision": "Revised 01",
            "sha256": l2_hash,
        })

        worker = TimetableProductionWorker(
            target_levels=(1, 2),
            mongo_repo=self.repo,
        )
        worker.discover_and_select_candidates = MagicMock(
            return_value=({1: cand1, 2: cand2}, {}, (2024, 1, "2024/2025", "Semester I"))
        )

        parsed1 = self._create_mock_parsed(level=1, sha_content=b"pdf_content_l1")
        with patch("src.worker.TimetablePDFParser") as mock_parser_cls:
            mock_parser = MagicMock()
            mock_parser.parse_pdf.return_value = parsed1
            mock_parser_cls.return_value = mock_parser

            exit_code = worker.run()

        self.assertEqual(exit_code, 0)
        # Level 1 metadata is upserted
        doc_l1 = self.fake_tt_col.find_one({"level": 1})
        self.assertIsNotNone(doc_l1)
        self.assertEqual(doc_l1["sha256"], hashlib.sha256(b"pdf_content_l1").hexdigest())

        # Level 1 session is synced
        sess_l1 = self.fake_sess_col.find_one({"level": 1})
        self.assertIsNotNone(sess_l1)
        self.assertEqual(sess_l1["subjectCode"], "CMIS 1113")

        # Level 2 was untouched
        self.assertEqual(len(self.fake_sess_col.find({"level": 2})), 0)

    def test_revised_pdf_synchronization_and_stale_cleanup(self):
        """Revised PDF updates metadata and cleans up stale sessions for that level."""
        old_hash = hashlib.sha256(b"old_data").hexdigest()
        new_hash = hashlib.sha256(b"new_data").hexdigest()

        # Seed DB with old metadata and an old session
        self.fake_tt_col.docs.append({
            "_id": "doc_1",
            "level": 1,
            "academicYear": "2024/2025",
            "semester": "Semester I",
            "revision": "Original",
            "sha256": old_hash,
        })
        self.fake_sess_col.docs.append({
            "level": 1,
            "academicYear": "2024/2025",
            "semester": "Semester I",
            "day": "Monday",
            "startTime": "08:30",
            "endTime": "09:30",
            "subjectCode": "OLD 1113",
            "group": None,
            "sourcePdfHash": old_hash,
        })

        cand = self._create_mock_candidate(level=1, revision="Revised 01", sha_content=b"new_data")
        parsed = self._create_mock_parsed(level=1, revision="Revised 01", sha_content=b"new_data")

        worker = TimetableProductionWorker(
            target_levels=(1,),
            mongo_repo=self.repo,
        )
        worker.discover_and_select_candidates = MagicMock(
            return_value=({1: cand}, {}, (2024, 1, "2024/2025", "Semester I"))
        )

        with patch("src.worker.TimetablePDFParser") as mock_parser_cls:
            mock_parser = MagicMock()
            mock_parser.parse_pdf.return_value = parsed
            mock_parser_cls.return_value = mock_parser

            exit_code = worker.run()

        self.assertEqual(exit_code, 0)
        # Verify metadata updated to new hash
        doc = self.fake_tt_col.find_one({"level": 1})
        self.assertEqual(doc["sha256"], new_hash)
        self.assertEqual(doc["revision"], "Revised 01")

        # Verify old session was deleted and new session exists
        old_sess = self.fake_sess_col.find_one({"subjectCode": "OLD 1113"})
        self.assertIsNone(old_sess)
        new_sess = self.fake_sess_col.find_one({"subjectCode": "CMIS 1113"})
        self.assertIsNotNone(new_sess)
        self.assertEqual(new_sess["sourcePdfHash"], new_hash)

    def test_pdf_download_failure_preserves_database(self):
        """If PDF bytes cannot be downloaded, existing database records remain untouched."""
        cand = self._create_mock_candidate(level=1, sha_content=None)
        cand.pdf_bytes = None

        self.fake_tt_col.docs.append({
            "level": 1,
            "academicYear": "2024/2025",
            "semester": "Semester I",
            "revision": "Original",
            "sha256": "original_hash",
        })

        worker = TimetableProductionWorker(
            target_levels=(1,),
            mongo_repo=self.repo,
        )
        worker.discover_and_select_candidates = MagicMock(
            return_value=({1: cand}, {}, (2024, 1, "2024/2025", "Semester I"))
        )
        # Mock fetcher to fail
        worker.fetcher.fetch_pdf_data = MagicMock(return_value=None)

        exit_code = worker.run()
        self.assertEqual(exit_code, 1)

        # Database remains untouched
        doc = self.fake_tt_col.find_one({"level": 1})
        self.assertEqual(doc["sha256"], "original_hash")

    def test_parsing_failure_preserves_database(self):
        """If parser fails, existing data remains intact and exit code is nonzero."""
        cand = self._create_mock_candidate(level=1, sha_content=b"invalid_pdf_data")
        self.fake_tt_col.docs.append({
            "level": 1,
            "academicYear": "2024/2025",
            "semester": "Semester I",
            "revision": "Original",
            "sha256": "original_hash",
        })

        worker = TimetableProductionWorker(
            target_levels=(1,),
            mongo_repo=self.repo,
        )
        worker.discover_and_select_candidates = MagicMock(
            return_value=({1: cand}, {}, (2024, 1, "2024/2025", "Semester I"))
        )

        with patch("src.worker.TimetablePDFParser") as mock_parser_cls:
            mock_parser = MagicMock()
            mock_parser.parse_pdf.side_effect = ValueError("Corrupt PDF table structure")
            mock_parser_cls.return_value = mock_parser

            exit_code = worker.run()

        self.assertEqual(exit_code, 1)
        doc = self.fake_tt_col.find_one({"level": 1})
        self.assertEqual(doc["sha256"], "original_hash")

    def test_validation_failure_preserves_database(self):
        """If parsed candidate fails validation, database is not overwritten."""
        cand = self._create_mock_candidate(level=1, sha_content=b"some_pdf")
        self.fake_tt_col.docs.append({
            "level": 1,
            "academicYear": "2024/2025",
            "semester": "Semester I",
            "revision": "Original",
            "sha256": "original_hash",
        })

        # Parsed with 0 sessions (validation failure)
        parsed = self._create_mock_parsed(level=1, sha_content=b"some_pdf")
        parsed.sessions = []
        parsed.total_sessions = 0

        worker = TimetableProductionWorker(
            target_levels=(1,),
            mongo_repo=self.repo,
        )
        worker.discover_and_select_candidates = MagicMock(
            return_value=({1: cand}, {}, (2024, 1, "2024/2025", "Semester I"))
        )

        with patch("src.worker.TimetablePDFParser") as mock_parser_cls:
            mock_parser = MagicMock()
            mock_parser.parse_pdf.return_value = parsed
            mock_parser_cls.return_value = mock_parser

            exit_code = worker.run()

        self.assertEqual(exit_code, 1)
        doc = self.fake_tt_col.find_one({"level": 1})
        self.assertEqual(doc["sha256"], "original_hash")
        self.assertEqual(len(self.fake_sess_col.docs), 0)

    def test_mongodb_sync_failure_handling(self):
        """If MongoDB synchronization fails, error is logged and exit code is nonzero."""
        cand = self._create_mock_candidate(level=1, sha_content=b"new_data")
        parsed = self._create_mock_parsed(level=1, sha_content=b"new_data")

        worker = TimetableProductionWorker(
            target_levels=(1,),
            mongo_repo=self.repo,
        )
        worker.discover_and_select_candidates = MagicMock(
            return_value=({1: cand}, {}, (2024, 1, "2024/2025", "Semester I"))
        )

        with patch("src.worker.TimetablePDFParser") as mock_parser_cls:
            mock_parser = MagicMock()
            mock_parser.parse_pdf.return_value = parsed
            mock_parser_cls.return_value = mock_parser

            # Mock repo method to raise MongoRepositoryError
            self.repo.sync_level_atomic = MagicMock(
                side_effect=MongoRepositoryError("Write conflict in sessions")
            )

            exit_code = worker.run()

        self.assertEqual(exit_code, 1)

    def test_temporary_pdf_cleanup_guarantee(self):
        """Verify temporary directory and candidate PDF are removed upon completion."""
        cand = self._create_mock_candidate(level=1, sha_content=b"temporary_pdf_data")
        parsed = self._create_mock_parsed(level=1, sha_content=b"temporary_pdf_data")

        worker = TimetableProductionWorker(
            target_levels=(1,),
            mongo_repo=self.repo,
        )
        worker.discover_and_select_candidates = MagicMock(
            return_value=({1: cand}, {}, (2024, 1, "2024/2025", "Semester I"))
        )

        created_temp_dirs = []
        original_tempdir = tempfile.TemporaryDirectory

        def tracking_tempdir(*args, **kwargs):
            td = original_tempdir(*args, **kwargs)
            created_temp_dirs.append(Path(td.name))
            return td

        with patch("src.worker.tempfile.TemporaryDirectory", side_effect=tracking_tempdir):
            with patch("src.worker.TimetablePDFParser") as mock_parser_cls:
                mock_parser = MagicMock()
                mock_parser.parse_pdf.return_value = parsed
                mock_parser_cls.return_value = mock_parser

                exit_code = worker.run()

        self.assertEqual(exit_code, 0)
        self.assertGreater(len(created_temp_dirs), 0)
        # Verify that all tracked temporary directories no longer exist on disk
        for td in created_temp_dirs:
            self.assertFalse(td.exists(), f"Temporary directory {td} was not cleaned up!")

    def test_dry_run_mode_makes_no_writes(self):
        """Dry-run mode discovers candidates and changes but makes zero database writes."""
        cand = self._create_mock_candidate(level=1, sha_content=b"new_data")

        worker = TimetableProductionWorker(
            target_levels=(1,),
            mongo_repo=self.repo,
            dry_run=True,
        )
        worker.discover_and_select_candidates = MagicMock(
            return_value=({1: cand}, {}, (2024, 1, "2024/2025", "Semester I"))
        )

        with patch("src.worker.TimetablePDFParser") as mock_parser_cls:
            exit_code = worker.run()

        self.assertEqual(exit_code, 0)
        # Ensure no database writes or parser calls occurred
        mock_parser_cls.assert_not_called()
        self.assertEqual(len(self.fake_tt_col.docs), 0)
        self.assertEqual(len(self.fake_sess_col.docs), 0)

    def test_no_notices_found_exits_nonzero(self):
        """When scraper discovers no notices, worker exits with code 1."""
        worker = TimetableProductionWorker(
            target_levels=(1,),
            mongo_repo=self.repo,
        )
        worker.scraper.discover_notices = MagicMock(return_value=[])

        exit_code = worker.run()
        self.assertEqual(exit_code, 1)

    def test_isolation_between_levels_and_terms(self):
        """Updating Level 1 does not delete or alter Level 2 or sessions in another term."""
        cand1 = self._create_mock_candidate(level=1, sha_content=b"content_1_new")
        parsed1 = self._create_mock_parsed(level=1, sha_content=b"content_1_new")

        # Seed database with Level 2 session in same term, and Level 1 session in a different semester
        self.fake_sess_col.docs.append({
            "level": 2,
            "academicYear": "2024/2025",
            "semester": "Semester I",
            "day": "Tuesday",
            "startTime": "09:30",
            "endTime": "10:30",
            "subjectCode": "CMIS 2113",
            "group": None,
            "sourcePdfHash": "hash_l2",
        })
        self.fake_sess_col.docs.append({
            "level": 1,
            "academicYear": "2023/2024",
            "semester": "Semester II",
            "day": "Monday",
            "startTime": "08:30",
            "endTime": "09:30",
            "subjectCode": "CMIS 1213",
            "group": None,
            "sourcePdfHash": "hash_other_term",
        })

        worker = TimetableProductionWorker(
            target_levels=(1,),
            mongo_repo=self.repo,
        )
        worker.discover_and_select_candidates = MagicMock(
            return_value=({1: cand1}, {}, (2024, 1, "2024/2025", "Semester I"))
        )

        with patch("src.worker.TimetablePDFParser") as mock_parser_cls:
            mock_parser = MagicMock()
            mock_parser.parse_pdf.return_value = parsed1
            mock_parser_cls.return_value = mock_parser

            exit_code = worker.run()

        self.assertEqual(exit_code, 0)

        # Level 2 session is still intact
        l2_sess = self.fake_sess_col.find_one({"level": 2})
        self.assertIsNotNone(l2_sess)
        self.assertEqual(l2_sess["subjectCode"], "CMIS 2113")

        # Level 1 session from different semester is still intact
        other_term_sess = self.fake_sess_col.find_one({"academicYear": "2023/2024"})
        self.assertIsNotNone(other_term_sess)
        self.assertEqual(other_term_sess["subjectCode"], "CMIS 1213")

    def test_new_academic_term_preserves_older_term_records(self):
        """Newly published academic year/semester does not delete prior term records."""
        # 1. Seed existing older academic term in DB (2024/2025 Semester I)
        self.fake_tt_col.docs.append({
            "_id": "doc_old_term",
            "level": 1,
            "academicYear": "2024/2025",
            "semester": "Semester I",
            "revision": "Revised 02",
            "sha256": "old_term_hash",
        })
        self.fake_sess_col.docs.append({
            "timetableId": "doc_old_term",
            "level": 1,
            "academicYear": "2024/2025",
            "semester": "Semester I",
            "day": "Monday",
            "startTime": "08:30",
            "endTime": "09:30",
            "subjectCode": "CMIS 1113",
            "group": None,
            "sourcePdfHash": "old_term_hash",
        })

        # 2. Candidate for new academic term (2025/2026 Semester I)
        cand_new_term = self._create_mock_candidate(level=1, sha_content=b"new_term_pdf")
        cand_new_term.academic_year = "2025/2026"
        cand_new_term.academic_year_start = 2025
        cand_new_term.semester = "Semester I"

        parsed_new_term = self._create_mock_parsed(level=1, sha_content=b"new_term_pdf")
        parsed_new_term.academic_year = "2025/2026"
        parsed_new_term.semester = "Semester I"

        worker = TimetableProductionWorker(
            target_levels=(1,),
            mongo_repo=self.repo,
        )
        worker.discover_and_select_candidates = MagicMock(
            return_value=({1: cand_new_term}, {}, (2025, 1, "2025/2026", "Semester I"))
        )

        with patch("src.worker.TimetablePDFParser") as mock_parser_cls:
            mock_parser = MagicMock()
            mock_parser.parse_pdf.return_value = parsed_new_term
            mock_parser_cls.return_value = mock_parser

            exit_code = worker.run()

        self.assertEqual(exit_code, 0)

        # Verify older term metadata remains intact
        old_tt = self.fake_tt_col.find_one({"academicYear": "2024/2025", "semester": "Semester I"})
        self.assertIsNotNone(old_tt)
        self.assertEqual(old_tt["sha256"], "old_term_hash")

        # Verify new term metadata exists
        new_tt = self.fake_tt_col.find_one({"academicYear": "2025/2026", "semester": "Semester I"})
        self.assertIsNotNone(new_tt)

        # Verify older term session remains intact
        old_sess = self.fake_sess_col.find_one({"academicYear": "2024/2025"})
        self.assertIsNotNone(old_sess)
        self.assertEqual(old_sess["subjectCode"], "CMIS 1113")

        # Verify new term session exists
        new_sess = self.fake_sess_col.find_one({"academicYear": "2025/2026"})
        self.assertIsNotNone(new_sess)

    def test_source_metadata_has_no_invalid_local_path(self):
        """Metadata persisted to MongoDB has localPath as None after temporary cleanup."""
        cand = self._create_mock_candidate(level=1, sha_content=b"data_for_path_test")
        parsed = self._create_mock_parsed(level=1, sha_content=b"data_for_path_test")

        worker = TimetableProductionWorker(
            target_levels=(1,),
            mongo_repo=self.repo,
        )
        worker.discover_and_select_candidates = MagicMock(
            return_value=({1: cand}, {}, (2024, 1, "2024/2025", "Semester I"))
        )

        with patch("src.worker.TimetablePDFParser") as mock_parser_cls:
            mock_parser = MagicMock()
            mock_parser.parse_pdf.return_value = parsed
            mock_parser_cls.return_value = mock_parser

            exit_code = worker.run()

        self.assertEqual(exit_code, 0)
        doc = self.fake_tt_col.find_one({"level": 1})
        self.assertIsNotNone(doc)
        # Confirm localPath is None (not pointing to deleted temporary path)
        self.assertIsNone(doc.get("localPath"))

    def test_simulated_mid_sync_failure_preserves_data(self):
        """Simulated failure during atomic sync leaves previous working timetable intact."""
        old_hash = hashlib.sha256(b"working_v1").hexdigest()
        self.fake_tt_col.docs.append({
            "_id": "doc_l1_intact",
            "level": 1,
            "academicYear": "2024/2025",
            "semester": "Semester I",
            "revision": "Original",
            "sha256": old_hash,
        })
        self.fake_sess_col.docs.append({
            "timetableId": "doc_l1_intact",
            "level": 1,
            "academicYear": "2024/2025",
            "semester": "Semester I",
            "day": "Monday",
            "startTime": "08:30",
            "endTime": "09:30",
            "subjectCode": "CMIS 1113",
            "group": None,
            "sourcePdfHash": old_hash,
        })

        cand = self._create_mock_candidate(level=1, revision="Revised 01", sha_content=b"new_failing_v2")
        parsed = self._create_mock_parsed(level=1, revision="Revised 01", sha_content=b"new_failing_v2")

        worker = TimetableProductionWorker(
            target_levels=(1,),
            mongo_repo=self.repo,
        )
        worker.discover_and_select_candidates = MagicMock(
            return_value=({1: cand}, {}, (2024, 1, "2024/2025", "Semester I"))
        )

        with patch("src.worker.TimetablePDFParser") as mock_parser_cls:
            mock_parser = MagicMock()
            mock_parser.parse_pdf.return_value = parsed
            mock_parser_cls.return_value = mock_parser

            # Simulate repository sync failure midway
            with patch.object(self.repo, "sync_level_atomic", side_effect=MongoRepositoryError("Network drop mid-sync")):
                exit_code = worker.run()

        self.assertEqual(exit_code, 1)

        # Verify old metadata was not overwritten
        doc = self.fake_tt_col.find_one({"level": 1})
        self.assertEqual(doc["sha256"], old_hash)
        self.assertEqual(doc["revision"], "Original")

        # Verify old session was not wiped
        sess = self.fake_sess_col.find_one({"level": 1})
        self.assertIsNotNone(sess)
        self.assertEqual(sess["sourcePdfHash"], old_hash)


if __name__ == "__main__":
    unittest.main()
