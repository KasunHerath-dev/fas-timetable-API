"""Unit tests for FastAPI Academic Calendar API endpoints."""

import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from src.api import app, get_repository
from src.mongodb_repository import MongoRepositoryError


class TestCalendarAPI(unittest.TestCase):

    def setUp(self):
        self.mock_repo = MagicMock()
        app.dependency_overrides[get_repository] = lambda: self.mock_repo
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def _sample_calendar(self):
        return {
            "id": "doc123",
            "calendarId": "cal_2024_2025_approved_12345678",
            "academicYear": "2024/2025",
            "academicYearStart": 2024,
            "academicYearEnd": 2025,
            "documentTitle": "CALENDAR OF DATES",
            "documentStatus": "approved",
            "revision": "Original",
            "levels": [1, 2, 3, 4],
            "semesters": ["Semester I", "Semester II"],
            "sourceUrl": "https://fas.wyb.ac.lk/uploads/COD-2024-2025.pdf",
            "signatureDate": "2026-07-03",
            "publicationDate": "2026-07-17",
            "sha256": "abcdef1234567890",
            "validationStatus": "VALID",
            "isCurrent": True,
            "isCurrentConfirmed": True,
            "selectionReason": "Verified official calendar for academic year 2024/2025",
            "activitiesCount": 3,
            "activities": [
                {
                    "activity": "Academic Session",
                    "category": "academic_session",
                    "semester": "Semester I",
                    "startDate": "2026-08-03",
                    "endDate": "2026-09-27",
                    "durationRaw": "08 Weeks",
                    "durationWeeks": 8.0,
                    "validationStatus": "VALID",
                    "warnings": [],
                },
                {
                    "activity": "Mid Semester Vacation",
                    "category": "mid_semester_vacation",
                    "semester": "Semester I",
                    "startDate": "2026-09-28",
                    "endDate": "2026-10-04",
                    "durationRaw": "01 Week",
                    "durationWeeks": 1.0,
                    "validationStatus": "VALID",
                    "warnings": [],
                },
                {
                    "activity": "Academic Session",
                    "category": "academic_session",
                    "semester": "Semester II",
                    "startDate": "2027-01-18",
                    "endDate": "2027-04-11",
                    "durationRaw": "12 Weeks",
                    "durationWeeks": 12.0,
                    "validationStatus": "VALID",
                    "warnings": [],
                },
            ],
        }

    def test_list_academic_calendars(self):
        self.mock_repo.get_academic_calendars.return_value = [self._sample_calendar()]
        resp = self.client.get("/api/academic-calendar")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["academicYear"], "2024/2025")

    def test_get_current_academic_calendar(self):
        self.mock_repo.get_current_academic_calendar.return_value = self._sample_calendar()
        resp = self.client.get("/api/academic-calendar/current")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["academicYear"], "2024/2025")
        self.assertTrue(data["isCurrent"])
        self.assertTrue(data["isCurrentConfirmed"])

    def test_get_current_academic_calendar_not_found(self):
        self.mock_repo.get_current_academic_calendar.return_value = None
        resp = self.client.get("/api/academic-calendar/current")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("No official academic calendar found", resp.json()["detail"])

    def test_get_calendar_by_academic_year(self):
        self.mock_repo.get_academic_calendar_by_year.return_value = self._sample_calendar()
        resp = self.client.get("/api/academic-calendar/2024-2025")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["academicYear"], "2024/2025")

    def test_get_calendar_by_academic_year_not_found(self):
        self.mock_repo.get_academic_calendar_by_year.return_value = None
        resp = self.client.get("/api/academic-calendar/2020-2021")
        self.assertEqual(resp.status_code, 404)

    def test_get_calendar_semester(self):
        self.mock_repo.get_academic_calendar_by_year.return_value = self._sample_calendar()
        resp = self.client.get("/api/academic-calendar/2024-2025/semesters/Semester I")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["academicYear"], "2024/2025")
        self.assertEqual(data["semester"], "Semester I")
        self.assertEqual(data["totalActivities"], 2)
        self.assertEqual(data["startDate"], "2026-08-03")
        self.assertEqual(data["endDate"], "2026-10-04")

    def test_get_calendar_semester_numeric_param(self):
        self.mock_repo.get_academic_calendar_by_year.return_value = self._sample_calendar()
        resp = self.client.get("/api/academic-calendar/2024-2025/semesters/2")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["semester"], "Semester II")
        self.assertEqual(data["totalActivities"], 1)

    def test_get_upcoming_activities(self):
        self.mock_repo.get_current_academic_calendar.return_value = self._sample_calendar()
        # Reference date inside semester I
        resp = self.client.get("/api/academic-calendar/upcoming?reference_date=2026-09-01&limit=5")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["referenceDate"], "2026-09-01")
        self.assertGreaterEqual(len(data["activities"]), 1)
        first_act = data["activities"][0]
        self.assertEqual(first_act["activity"], "Academic Session")
        self.assertEqual(first_act["status"], "ongoing")

    def test_get_academic_calendar_status(self):
        self.mock_repo.get_calendar_sync_status.return_value = {
            "lastCheckedAt": "2026-10-20T12:00:00+05:30",
            "lastSuccessfulSyncAt": "2026-10-20T12:00:00+05:30",
            "sourcePageUrl": "https://fas.wyb.ac.lk/timetables/academic-calendar/",
            "discoverySuccess": True,
            "newerDocumentDiscovered": False,
            "documentAwaitingValidation": False,
            "currentCalendarConfirmed": True,
            "currentCalendarId": "cal_2024_2025_approved_12345678",
            "currentAcademicYear": "2024/2025",
            "lastRunFailed": False,
            "discoveredDocumentsCount": 6,
            "unchangedCount": 6,
            "synchronizedCount": 0,
            "failedCount": 0,
            "lastError": None,
        }
        resp = self.client.get("/api/academic-calendar/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["discoverySuccess"])
        self.assertTrue(data["currentCalendarConfirmed"])
        self.assertEqual(data["discoveredDocumentsCount"], 6)

    def test_service_unavailable_error_handling(self):
        self.mock_repo.get_academic_calendars.side_effect = MongoRepositoryError("Atlas timeout")
        resp = self.client.get("/api/academic-calendar")
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json()["detail"], "Database service unavailable")
