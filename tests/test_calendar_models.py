"""Unit tests for Academic Calendar data models."""

import unittest
from src.calendar_models import (
    CalendarActivity,
    ActivityCategory,
    CalendarStatus,
    CalendarValidationStatus,
    AcademicCalendarRecord,
    CalendarSyncStatus,
)


class TestCalendarModels(unittest.TestCase):

    def test_calendar_activity_valid(self):
        activity = CalendarActivity(
            activity="Academic Session",
            category=ActivityCategory.ACADEMIC_SESSION,
            semester="Semester I",
            startDate="2026-08-03",
            endDate="2026-09-27",
            durationRaw="08 Weeks",
            durationWeeks=8.0,
            validationStatus=CalendarValidationStatus.VALID,
        )
        self.assertEqual(activity.activity, "Academic Session")
        self.assertEqual(activity.category, ActivityCategory.ACADEMIC_SESSION)
        self.assertEqual(activity.semester, "Semester I")
        self.assertEqual(activity.startDate, "2026-08-03")
        self.assertEqual(activity.endDate, "2026-09-27")
        self.assertEqual(activity.durationWeeks, 8.0)
        self.assertEqual(activity.validationStatus, CalendarValidationStatus.VALID)

    def test_academic_calendar_record_serialization(self):
        record = AcademicCalendarRecord(
            calendarId="cal_2024_2025_approved_12345678",
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
            sha256="1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            firstSeenAt="2026-10-20T12:00:00+05:30",
            lastSeenAt="2026-10-20T12:00:00+05:30",
            lastValidatedAt="2026-10-20T12:00:00+05:30",
            parserVersion="1.0.0",
            validationStatus=CalendarValidationStatus.VALID,
            activitiesCount=1,
            activities=[
                CalendarActivity(
                    activity="Academic Session",
                    category=ActivityCategory.ACADEMIC_SESSION,
                    semester="Semester I",
                    startDate="2026-08-03",
                    endDate="2026-09-27",
                    durationRaw="08 Weeks",
                    durationWeeks=8.0,
                )
            ],
            isCurrent=True,
            isCurrentConfirmed=True,
            selectionReason="Verified official calendar",
            updatedAt="2026-10-20T12:00:00+05:30",
        )
        data = record.model_dump()
        self.assertEqual(data["calendarId"], "cal_2024_2025_approved_12345678")
        self.assertEqual(data["academicYear"], "2024/2025")
        self.assertEqual(data["documentStatus"], "approved")
        self.assertTrue(data["isCurrent"])
        self.assertEqual(len(data["activities"]), 1)

    def test_calendar_sync_status(self):
        status = CalendarSyncStatus(
            lastCheckedAt="2026-10-20T12:00:00+05:30",
            sourcePageUrl="https://fas.wyb.ac.lk/timetables/academic-calendar/",
            discoverySuccess=True,
            currentCalendarConfirmed=True,
            updatedAt="2026-10-20T12:00:00+05:30",
        )
        self.assertTrue(status.discoverySuccess)
        self.assertTrue(status.currentCalendarConfirmed)
        self.assertIsNone(status.lastError)
