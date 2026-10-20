"""Unit tests for MongoDB Academic Calendar repository operations."""

import unittest
from unittest.mock import MagicMock
from src.calendar_repository import MongoCalendarRepository
from src.calendar_models import (
    AcademicCalendarRecord,
    CalendarStatus,
    CalendarValidationStatus,
)


class FakeMongoCollection:
    def __init__(self):
        self.docs = []
        self.indexes = []

    def create_index(self, keys, **kwargs):
        self.indexes.append({"keys": keys, **kwargs})
        return kwargs.get("name", "idx")

    def find_one(self, filter_query, sort=None):
        for doc in self.docs:
            match = True
            for k, v in filter_query.items():
                if k == "$ne" or isinstance(v, dict) and "$ne" in v:
                    ne_val = v["$ne"]
                    if doc.get(k) == ne_val:
                        match = False
                        break
                elif doc.get(k) != v:
                    match = False
                    break
            if match:
                return dict(doc)
        return None

    def find(self, filter_query=None):
        filter_query = filter_query or {}
        matches = []
        for doc in self.docs:
            match = True
            for k, v in filter_query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                matches.append(dict(doc))

        cursor = MagicMock()
        cursor.sort.return_value = matches
        cursor.__iter__.return_value = iter(matches)
        return cursor

    def update_one(self, filter_query, update_dict, upsert=False):
        set_data = update_dict.get("$set", {})
        res = MagicMock()
        for idx, doc in enumerate(self.docs):
            match = True
            for k, v in filter_query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                self.docs[idx].update(set_data)
                res.upserted_id = None
                res.modified_count = 1
                return res

        if upsert:
            new_doc = dict(set_data)
            new_doc.update(filter_query)
            if "_id" not in filter_query:
                new_doc["_id"] = f"id_{len(self.docs) + 1}"
            self.docs.append(new_doc)
            res.upserted_id = new_doc["_id"]
            res.modified_count = 0
            return res

        res.upserted_id = None
        res.modified_count = 0
        return res

    def update_many(self, filter_query, update_dict):
        set_data = update_dict.get("$set", {})
        for idx, doc in enumerate(self.docs):
            match = True
            for k, v in filter_query.items():
                if isinstance(v, dict) and "$ne" in v:
                    if doc.get(k) == v["$ne"]:
                        match = False
                        break
                elif doc.get(k) != v:
                    match = False
                    break
            if match:
                self.docs[idx].update(set_data)


class TestMongoCalendarRepository(unittest.TestCase):

    def setUp(self):
        self.fake_cal_col = FakeMongoCollection()
        self.fake_status_col = FakeMongoCollection()
        self.fake_db = MagicMock()
        self.fake_db.__getitem__.side_effect = lambda name: (
            self.fake_status_col if "status" in name else self.fake_cal_col
        )
        self.fake_client = MagicMock()
        self.fake_client.__getitem__.return_value = self.fake_db

        self.repo = MongoCalendarRepository(
            uri="mongodb://localhost:27017",
            database_name="test_db",
            collection_name="academic_calendars",
            status_collection_name="calendar_sync_status",
            client=self.fake_client,
        )

    def _sample_record(self, cal_id="cal_2024_2025", sha256="hash123") -> AcademicCalendarRecord:
        return AcademicCalendarRecord(
            calendarId=cal_id,
            academicYear="2024/2025",
            academicYearStart=2024,
            academicYearEnd=2025,
            documentTitle="CALENDAR OF DATES",
            documentStatus=CalendarStatus.APPROVED,
            revision="Original",
            revisionRank=2,
            levels=[1, 2, 3, 4],
            semesters=["Semester I", "Semester II"],
            sourceUrl="https://fas.wyb.ac.lk/uploads/COD-2024-2025.pdf",
            sha256=sha256,
            firstSeenAt="2026-10-20T12:00:00+05:30",
            lastSeenAt="2026-10-20T12:00:00+05:30",
            lastValidatedAt="2026-10-20T12:00:00+05:30",
            validationStatus=CalendarValidationStatus.VALID,
            activitiesCount=0,
            activities=[],
            updatedAt="2026-10-20T12:00:00+05:30",
        )

    def test_upsert_new_calendar(self):
        rec = self._sample_record()
        res = self.repo.upsert_calendar(rec, is_current=True, is_confirmed=True)
        self.assertEqual(res["action"], "upserted")
        self.assertEqual(len(self.fake_cal_col.docs), 1)
        self.assertTrue(self.fake_cal_col.docs[0]["isCurrent"])

    def test_upsert_unchanged_skips_full_write(self):
        rec = self._sample_record()
        self.repo.upsert_calendar(rec, is_current=True)
        # Second call with identical hash
        res = self.repo.upsert_calendar(rec, is_current=True)
        self.assertEqual(res["action"], "skipped")
        self.assertEqual(len(self.fake_cal_col.docs), 1)

    def test_revision_history_preserved_on_changed_hash(self):
        rec1 = self._sample_record(sha256="initial_hash")
        self.repo.upsert_calendar(rec1)

        # Update with new content hash
        rec2 = self._sample_record(sha256="revised_hash")
        res = self.repo.upsert_calendar(rec2)
        self.assertEqual(res["action"], "updated")

        saved = self.fake_cal_col.docs[0]
        self.assertEqual(saved["sha256"], "revised_hash")
        self.assertEqual(len(saved["revisionHistory"]), 1)
        self.assertEqual(saved["revisionHistory"][0]["sha256"], "initial_hash")

    def test_get_current_and_by_year(self):
        rec = self._sample_record()
        self.repo.upsert_calendar(rec, is_current=True, is_confirmed=True)

        current = self.repo.get_current_calendar()
        self.assertIsNotNone(current)
        self.assertEqual(current["academicYear"], "2024/2025")

        by_year = self.repo.get_calendar_by_academic_year("2024-2025")
        self.assertIsNotNone(by_year)
        self.assertEqual(by_year["academicYear"], "2024/2025")

    def test_sync_status_lifecycle(self):
        initial = self.repo.get_sync_status()
        self.assertFalse(initial["discoverySuccess"])

        self.repo.update_sync_status({
            "lastCheckedAt": "2026-10-20T12:00:00+05:30",
            "discoverySuccess": True,
            "currentCalendarConfirmed": True,
        })
        updated = self.repo.get_sync_status()
        self.assertTrue(updated["discoverySuccess"])
        self.assertTrue(updated["currentCalendarConfirmed"])
