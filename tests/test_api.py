"""Unit tests for FastAPI backend API endpoints."""

import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from src.api import app, get_repository
from src.mongodb_repository import MongoRepositoryError


class TestTimetableAPI(unittest.TestCase):

    def setUp(self):
        self.mock_repo = MagicMock()
        # Override FastAPI dependency to use the mock repository
        app.dependency_overrides[get_repository] = lambda: self.mock_repo
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_health_check_connected(self):
        self.mock_repo.ping.return_value = True
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["database"], "connected")
        self.assertIn("timestamp", data)

    def test_health_check_database_offline(self):
        self.mock_repo.ping.side_effect = MongoRepositoryError("Connection timeout")
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["database"], "offline")

    def test_list_timetables(self):
        sample_timetables = [
            {
                "id": "doc1",
                "level": 1,
                "academicYear": "2024/2025",
                "semester": "Semester I",
                "revision": "Revised 02",
                "publicationDate": "2026-10-05",
            },
            {
                "id": "doc2",
                "level": 2,
                "academicYear": "2024/2025",
                "semester": "Semester I",
                "revision": "Revised 01",
                "publicationDate": "2026-09-10",
            },
        ]
        self.mock_repo.get_timetables.return_value = sample_timetables

        response = self.client.get("/api/timetables")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["level"], 1)

    def test_list_timetables_filter_level(self):
        self.mock_repo.get_timetables.return_value = [
            {
                "id": "doc1",
                "level": 1,
                "academicYear": "2024/2025",
                "semester": "Semester I",
            }
        ]
        response = self.client.get("/api/timetables?level=1")
        self.assertEqual(response.status_code, 200)
        self.mock_repo.get_timetables.assert_called_with(level=1)

    def test_list_timetables_invalid_level(self):
        response = self.client.get("/api/timetables?level=5")
        self.assertEqual(response.status_code, 422)

    def test_get_level_status(self):
        self.mock_repo.get_timetables.return_value = [
            {"level": 1, "academicYear": "2024/2025", "semester": "Semester I"}
        ]
        self.mock_repo.get_level_status.return_value = {
            "level": 1,
            "academicYear": "2024/2025",
            "semester": "Semester I",
            "totalSessions": 44,
            "validSessions": 40,
            "needsReviewSessions": 4,
            "sessionTypes": {"Lecture": 30, "Practical": 14},
        }

        response = self.client.get("/api/timetables/1/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["level"], 1)
        self.assertEqual(data["totalSessions"], 44)
        self.assertEqual(data["validSessions"], 40)
        self.assertEqual(data["needsReviewSessions"], 4)

    def test_get_level_sessions_with_filters(self):
        self.mock_repo.get_timetables.return_value = [
            {"level": 1, "academicYear": "2024/2025", "semester": "Semester I"}
        ]
        sample_sessions = [
            {
                "id": "s1",
                "level": 1,
                "academicYear": "2024/2025",
                "semester": "Semester I",
                "day": "Monday",
                "startTime": "08:30",
                "endTime": "09:30",
                "subjectCode": "CMIS 1113",
                "sessionType": "Lecture",
                "group": None,
                "location": "MH",
                "rawCellText": "CMIS 1113 (L)\nMH",
                "validationStatus": "VALID",
                "warnings": [],
            },
            {
                "id": "s2",
                "level": 1,
                "academicYear": "2024/2025",
                "semester": "Semester I",
                "day": "Thursday",
                "startTime": "10:30",
                "endTime": "11:30",
                "subjectCode": "ELPC 1+10",
                "sessionType": None,
                "group": None,
                "location": "Mini Auditorium",
                "rawCellText": "ELPC 1+10\nMini Auditorium",
                "validationStatus": "NEEDS_REVIEW",
                "warnings": ["Unusual character in subject code"],
            },
        ]
        self.mock_repo.get_sessions.return_value = sample_sessions

        response = self.client.get("/api/timetables/1/sessions?day=Monday&subjectCode=CMIS")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["level"], 1)
        self.assertEqual(data["day"], "Monday")
        self.assertEqual(data["subjectCode"], "CMIS")
        self.assertEqual(data["totalSessions"], 2)
        # Ensure NEEDS_REVIEW record is present and marked
        self.assertEqual(data["sessions"][1]["validationStatus"], "NEEDS_REVIEW")

    def test_get_level_sessions_invalid_day(self):
        response = self.client.get("/api/timetables/1/sessions?day=Saturday")
        self.assertEqual(response.status_code, 422)

    def test_database_error_handling(self):
        self.mock_repo.get_timetables.side_effect = MongoRepositoryError("Atlas query failed")
        response = self.client.get("/api/timetables")
        self.assertEqual(response.status_code, 503)
        self.assertIn("Database service unavailable", response.json()["detail"])

    def test_level_2_sessions_and_status(self):
        self.mock_repo.get_timetables.return_value = [
            {"level": 2, "academicYear": "2024/2025", "semester": "Semester I"}
        ]
        self.mock_repo.get_level_status.return_value = {
            "level": 2,
            "academicYear": "2024/2025",
            "semester": "Semester I",
            "totalSessions": 38,
            "validSessions": 38,
            "needsReviewSessions": 0,
            "sessionTypes": {"Lecture": 20, "Practical": 18},
        }
        self.mock_repo.get_sessions.return_value = [
            {
                "id": "s2-cmis",
                "level": 2,
                "academicYear": "2024/2025",
                "semester": "Semester I",
                "day": "Friday",
                "startTime": "12:30",
                "endTime": "14:30",
                "subjectCode": "CMIS 2113",
                "sessionType": "Practical",
                "group": "Gp. IV",
                "location": "LR-07",
                "rawCellText": "CMIS 2113 (P)\nGp. IV",
                "validationStatus": "VALID",
                "warnings": [],
            }
        ]

        # Test /api/timetables/2/status
        res_status = self.client.get("/api/timetables/2/status")
        self.assertEqual(res_status.status_code, 200)
        self.assertEqual(res_status.json()["level"], 2)

        # Test /api/timetables/2/sessions
        res_sessions = self.client.get("/api/timetables/2/sessions")
        self.assertEqual(res_sessions.status_code, 200)
        self.assertEqual(res_sessions.json()["level"], 2)
        self.assertEqual(len(res_sessions.json()["sessions"]), 1)
        self.assertEqual(res_sessions.json()["sessions"][0]["subjectCode"], "CMIS 2113")

    def test_unprefixed_serverless_routes(self):
        """Verify routes respond correctly if Vercel strips the /api prefix."""
        self.mock_repo.ping.return_value = True
        self.mock_repo.get_timetables.return_value = []

        res_health = self.client.get("/health")
        self.assertEqual(res_health.status_code, 200)
        self.assertEqual(res_health.json()["status"], "ok")

        res_timetables = self.client.get("/timetables")
        self.assertEqual(res_timetables.status_code, 200)

    def test_root_index_exports_app(self):
        """Verify root index.py and api/index.py export the identical FastAPI app."""
        import index
        import api.index
        self.assertIs(index.app, app)
        self.assertIs(api.index.app, app)


if __name__ == "__main__":
    unittest.main()
