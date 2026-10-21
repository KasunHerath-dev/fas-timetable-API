"""Unit tests for FAS WUSL Academic Calendar current calendar selector."""

import unittest
from src.calendar_models import (
    AcademicCalendarRecord,
    CalendarStatus,
    CalendarValidationStatus,
)
from src.calendar_selector import CalendarSelector


class TestCalendarSelector(unittest.TestCase):

    def _create_record(
        self,
        cal_id: str,
        academic_year: str,
        start_year: int,
        status: CalendarStatus,
        revision_rank: int,
        sig_date: str = "2026-07-03",
        pub_date: str = "2026-07-17",
        sha256: str = "hash1",
        semesters: list = None,
        val_status: CalendarValidationStatus = CalendarValidationStatus.VALID,
    ) -> AcademicCalendarRecord:
        return AcademicCalendarRecord(
            calendarId=cal_id,
            academicYear=academic_year,
            academicYearStart=start_year,
            academicYearEnd=start_year + 1,
            documentTitle=f"{status.value.upper()} CALENDAR OF DATES",
            documentStatus=status,
            revision=status.value.capitalize(),
            revisionRank=revision_rank,
            levels=[1, 2, 3, 4],
            semesters=semesters or ["Semester I"],
            sourceUrl=f"https://fas.wyb.ac.lk/{cal_id}.pdf",
            signatureDate=sig_date,
            publicationDate=pub_date,
            sha256=sha256,
            firstSeenAt="2026-10-20T12:00:00+05:30",
            lastSeenAt="2026-10-20T12:00:00+05:30",
            lastValidatedAt="2026-10-20T12:00:00+05:30",
            validationStatus=val_status,
            activitiesCount=5,
            activities=[],
            updatedAt="2026-10-20T12:00:00+05:30",
        )

    def test_select_highest_academic_period(self):
        cal_2023 = self._create_record("cal_2023", "2023/2024", 2023, CalendarStatus.APPROVED, 2)
        cal_2024 = self._create_record("cal_2024", "2024/2025", 2024, CalendarStatus.APPROVED, 2)

        selected, confirmed, reason = CalendarSelector.select_current_calendar([cal_2023, cal_2024])
        self.assertIsNotNone(selected)
        self.assertEqual(selected.calendarId, "cal_2024")
        self.assertTrue(confirmed)
        self.assertIn("2024/2025", reason)

    def test_prefer_revised_over_approved(self):
        cal_approved = self._create_record(
            "cal_approved", "2023/2024", 2023, CalendarStatus.APPROVED, 2, sig_date="2025-09-12"
        )
        cal_revised = self._create_record(
            "cal_revised", "2023/2024", 2023, CalendarStatus.REVISED, 3, sig_date="2025-12-12"
        )

        selected, confirmed, reason = CalendarSelector.select_current_calendar([cal_approved, cal_revised])
        self.assertEqual(selected.calendarId, "cal_revised")
        self.assertTrue(confirmed)
        self.assertIn("revised", reason.lower())

    def test_draft_not_treated_as_final_when_approved_exists_for_same_period(self):
        cal_approved = self._create_record("cal_app", "2024/2025", 2024, CalendarStatus.APPROVED, 2)
        cal_draft = self._create_record("cal_drf", "2024/2025", 2024, CalendarStatus.DRAFT, 1)

        selected, confirmed, reason = CalendarSelector.select_current_calendar([cal_approved, cal_draft])
        self.assertEqual(selected.calendarId, "cal_app")
        self.assertTrue(confirmed)

    def test_unconfirmed_when_only_draft_exists_for_new_academic_period(self):
        cal_2023_approved = self._create_record("cal_2023", "2023/2024", 2023, CalendarStatus.APPROVED, 2)
        cal_2024_draft = self._create_record("cal_2024_draft", "2024/2025", 2024, CalendarStatus.DRAFT, 1)

        selected, confirmed, reason = CalendarSelector.select_current_calendar([cal_2023_approved, cal_2024_draft])
        self.assertEqual(selected.calendarId, "cal_2024_draft")
        self.assertFalse(confirmed)
        self.assertIn("Draft", reason)

    def test_conflicting_documents_marked_unconfirmed(self):
        # Two approved documents for same year, same semester, different hashes, same signature date
        cal_a = self._create_record("cal_a", "2024/2025", 2024, CalendarStatus.APPROVED, 2, sha256="hashA", sig_date="2026-07-03")
        cal_b = self._create_record("cal_b", "2024/2025", 2024, CalendarStatus.APPROVED, 2, sha256="hashB", sig_date="2026-07-03")

        selected, confirmed, reason = CalendarSelector.select_current_calendar([cal_a, cal_b])
        self.assertFalse(confirmed)
        self.assertIn("Conflicting", reason)

    def test_discard_invalid_records(self):
        cal_invalid = self._create_record(
            "cal_inv", "2025/2026", 2025, CalendarStatus.APPROVED, 2,
            val_status=CalendarValidationStatus.INVALID
        )
        cal_valid = self._create_record("cal_val", "2024/2025", 2024, CalendarStatus.APPROVED, 2)

        selected, confirmed, reason = CalendarSelector.select_current_calendar([cal_invalid, cal_valid])
        self.assertEqual(selected.calendarId, "cal_val")
        self.assertTrue(confirmed)

    def test_newer_official_calendar_versus_older_revised_calendar(self):
        """A newer official calendar takes precedence over an older revised calendar."""
        cal_2023_revised = self._create_record(
            "cal_2023_revised", "2023/2024", 2023, CalendarStatus.REVISED, 3,
            pub_date="2025-12-15", sig_date="2025-12-12"
        )
        cal_2024_official = self._create_record(
            "cal_2024_official", "2024/2025", 2024, CalendarStatus.APPROVED, 2,
            pub_date="2026-07-17", sig_date="2026-07-03"
        )

        selected, confirmed, reason = CalendarSelector.select_current_calendar([cal_2023_revised, cal_2024_official])
        self.assertEqual(selected.calendarId, "cal_2024_official")
        self.assertEqual(selected.academicYear, "2024/2025")
        self.assertEqual(selected.documentStatus, CalendarStatus.APPROVED)
        self.assertTrue(confirmed)
        self.assertIn("2024/2025", reason)

    def test_newer_draft_versus_older_approved_or_revised_calendar(self):
        """A newer draft calendar takes precedence over an older approved calendar, with unconfirmed status."""
        cal_2024_approved = self._create_record(
            "cal_2024_app", "2024/2025", 2024, CalendarStatus.APPROVED, 2,
            pub_date="2026-07-17", sig_date="2026-07-03"
        )
        cal_2025_draft = self._create_record(
            "cal_2025_drf", "2025/2026", 2025, CalendarStatus.DRAFT, 1,
            pub_date="2027-01-10", sig_date="2027-01-05"
        )

        selected, confirmed, reason = CalendarSelector.select_current_calendar([cal_2024_approved, cal_2025_draft])
        self.assertEqual(selected.calendarId, "cal_2025_drf")
        self.assertEqual(selected.academicYear, "2025/2026")
        self.assertEqual(selected.documentStatus, CalendarStatus.DRAFT)
        self.assertFalse(confirmed)
        self.assertIn("Draft", reason)

    def test_same_academic_year_revisions(self):
        """Within the same academic year, a revised calendar supersedes the approved original."""
        cal_2024_original = self._create_record(
            "cal_2024_orig", "2024/2025", 2024, CalendarStatus.APPROVED, 2,
            pub_date="2026-07-17", sig_date="2026-07-03"
        )
        cal_2024_revised = self._create_record(
            "cal_2024_rev", "2024/2025", 2024, CalendarStatus.REVISED, 3,
            pub_date="2026-08-20", sig_date="2026-08-15"
        )

        selected, confirmed, reason = CalendarSelector.select_current_calendar([cal_2024_original, cal_2024_revised])
        self.assertEqual(selected.calendarId, "cal_2024_rev")
        self.assertTrue(confirmed)
        self.assertIn("revised", reason.lower())

    def test_academic_year_label_differs_from_gregorian_activity_dates(self):
        """Academic year identifier (2024/2025) is strictly preserved even if activities occur in 2026-2027."""
        from src.calendar_models import CalendarActivity, ActivityCategory
        cal = self._create_record(
            "cal_2024_gregorian_mismatch", "2024/2025", 2024, CalendarStatus.APPROVED, 2,
            pub_date="2026-07-17", sig_date="2026-07-03"
        )
        cal.activities = [
            CalendarActivity(
                activity="Academic Session",
                category=ActivityCategory.ACADEMIC_SESSION,
                semester="Semester I",
                startDate="2026-08-03",
                endDate="2026-09-27",
                durationRaw="08 Weeks",
                durationWeeks=8.0,
                validationStatus=CalendarValidationStatus.VALID,
            ),
            CalendarActivity(
                activity="Examination",
                category=ActivityCategory.EXAMINATION,
                semester="Semester II",
                startDate="2027-05-24",
                endDate="2027-06-20",
                durationRaw="04 Weeks",
                durationWeeks=4.0,
                validationStatus=CalendarValidationStatus.VALID,
            ),
        ]
        cal.activitiesCount = 2

        selected, confirmed, reason = CalendarSelector.select_current_calendar([cal])
        self.assertEqual(selected.calendarId, "cal_2024_gregorian_mismatch")
        self.assertEqual(selected.academicYear, "2024/2025")
        self.assertEqual(selected.activities[0].startDate, "2026-08-03")
        self.assertEqual(selected.activities[1].endDate, "2027-06-20")
        self.assertTrue(confirmed)

    def test_missing_publication_dates_or_ambiguous_status(self):
        """Missing publication dates falls back gracefully to academicYearStart, preserving UNKNOWN status."""
        cal_2023 = self._create_record(
            "cal_2023", "2023/2024", 2023, CalendarStatus.APPROVED, 2,
            pub_date=None, sig_date=None
        )
        cal_2024_unknown = self._create_record(
            "cal_2024_unk", "2024/2025", 2024, CalendarStatus.UNKNOWN, 0,
            pub_date=None, sig_date=None
        )

        selected, confirmed, reason = CalendarSelector.select_current_calendar([cal_2023, cal_2024_unknown])
        self.assertEqual(selected.calendarId, "cal_2024_unk")
        self.assertEqual(selected.academicYear, "2024/2025")
        self.assertEqual(selected.documentStatus, CalendarStatus.UNKNOWN)
        self.assertFalse(confirmed)
        self.assertIn("approval status cannot be established", reason)
