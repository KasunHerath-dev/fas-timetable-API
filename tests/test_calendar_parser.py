"""Unit tests for FAS WUSL Academic Calendar PDF parser."""

import unittest
from unittest.mock import MagicMock, patch
import pymupdf

from src.calendar_parser import (
    AcademicCalendarParser,
    parse_date_to_iso,
    categorize_activity,
    calculate_duration_weeks,
)
from src.calendar_models import (
    CalendarStatus,
    ActivityCategory,
    CalendarValidationStatus,
)


class TestAcademicCalendarParser(unittest.TestCase):

    def setUp(self):
        self.parser = AcademicCalendarParser()

    def test_parse_date_to_iso(self):
        self.assertEqual(parse_date_to_iso("03-08-2026"), "2026-08-03")
        self.assertEqual(parse_date_to_iso("09.03.2026"), "2026-03-09")
        self.assertEqual(parse_date_to_iso("31-12-2025"), "2025-12-31")
        self.assertIsNone(parse_date_to_iso("invalid-date"))
        self.assertIsNone(parse_date_to_iso("32-01-2026"))

    def test_categorize_activity(self):
        self.assertEqual(categorize_activity("Academic Session"), ActivityCategory.ACADEMIC_SESSION)
        self.assertEqual(categorize_activity("Academic Session contd......"), ActivityCategory.ACADEMIC_SESSION)
        self.assertEqual(categorize_activity("Mid Semester Vacation"), ActivityCategory.MID_SEMESTER_VACATION)
        self.assertEqual(categorize_activity("Study Leave"), ActivityCategory.STUDY_LEAVE)
        self.assertEqual(categorize_activity("Examination"), ActivityCategory.EXAMINATION)
        self.assertEqual(categorize_activity("Christmas Vacation"), ActivityCategory.CHRISTMAS_VACATION)
        self.assertEqual(categorize_activity("New Year Vacation"), ActivityCategory.NEW_YEAR_VACATION)
        self.assertEqual(categorize_activity("Special Vacation due to bad Weather Condition"), ActivityCategory.VACATION)
        self.assertEqual(categorize_activity("Convocation Rehearsal"), ActivityCategory.OTHER)

    def test_calculate_duration_weeks(self):
        self.assertEqual(calculate_duration_weeks("2026-08-03", "2026-09-27"), 8.0)
        self.assertEqual(calculate_duration_weeks("2026-09-28", "2026-10-04"), 1.0)
        self.assertIsNone(calculate_duration_weeks("2026-10-04", "2026-09-28"))

    def test_parse_pdf_digital_text(self):
        sample_text = """
        Faculty of Applied Sciences
        Wayamba University of Sri Lanka
        Kuliyapitiya
        B.Sc. (General/ Joint Major/ Honours) Degree Programmes
        CALENDAR OF DATES
        LEVEL 1, 2, 3, 4 – ACADEMIC YEAR 2024/2025
        FIRST SEMESTER
        From
        To
        Duration
        Academic Session
        03-08-2026
        27-09-2026
        08 Weeks
        Mid Semester Vacation
        28-09-2026
        04-10-2026
        01 Week
        Study Leave
        23-11-2026
        06-12-2026
        02 Weeks
        Examination
        07-12-2026
        20-12-2026
        02 Weeks
        SECOND SEMESTER
        From
        To
        Duration
        Academic Session
        18-01-2027
        11-04-2027
        12 Weeks
        Deputy Registrar
        Faculty of Applied Sciences
        03-07-2026
        """
        # Create an in-memory PDF using pymupdf
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 50), sample_text)
        pdf_bytes = doc.tobytes()
        doc.close()

        is_valid, record, warnings = self.parser.parse_pdf(
            pdf_input=pdf_bytes,
            source_url="https://fas.wyb.ac.lk/uploads/sample.pdf",
            notice_title="Calendar of Dates 2024/2025",
            publication_date="2026-07-17",
        )

        self.assertTrue(is_valid)
        self.assertIsNotNone(record)
        self.assertEqual(record.academicYear, "2024/2025")
        self.assertEqual(record.academicYearStart, 2024)
        self.assertEqual(record.academicYearEnd, 2025)
        self.assertEqual(record.documentStatus, CalendarStatus.APPROVED)
        self.assertEqual(record.levels, [1, 2, 3, 4])
        self.assertEqual(record.signatureDate, "2026-07-03")
        self.assertEqual(record.publicationDate, "2026-07-17")
        self.assertEqual(len(record.activities), 5)

        # Check first activity
        act1 = record.activities[0]
        self.assertEqual(act1.activity, "Academic Session")
        self.assertEqual(act1.category, ActivityCategory.ACADEMIC_SESSION)
        self.assertEqual(act1.semester, "Semester I")
        self.assertEqual(act1.startDate, "2026-08-03")
        self.assertEqual(act1.endDate, "2026-09-27")
        self.assertEqual(act1.durationWeeks, 8.0)

        # Check second semester activity
        act5 = record.activities[4]
        self.assertEqual(act5.semester, "Semester II")
        self.assertEqual(act5.startDate, "2027-01-18")
        self.assertEqual(act5.endDate, "2027-04-11")

    def test_parse_pdf_revised_status(self):
        sample_text = """
        Faculty of Applied Sciences
        REVISED CALENDAR OF DATES
        LEVEL 1, 2, 4 – ACADEMIC YEAR 2023/2024
        FIRST SEMESTER
        Academic Session
        15-09-2025
        09-11-2025
        08 Weeks
        Deputy Registrar
        12-12-2025
        """
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 50), sample_text)
        pdf_bytes = doc.tobytes()
        doc.close()

        is_valid, record, warnings = self.parser.parse_pdf(pdf_bytes)
        self.assertTrue(is_valid)
        self.assertEqual(record.documentStatus, CalendarStatus.REVISED)
        self.assertEqual(record.revisionRank, 3)
        self.assertEqual(record.signatureDate, "2025-12-12")

    def test_parse_pdf_draft_status(self):
        sample_text = """
        Faculty of Applied Sciences
        DRAFT CALENDAR OF DATES
        LEVEL 1, 2, 3, 4 – ACADEMIC YEAR 2023/2024
        SECOND SEMESTER
        Academic Session
        09.03.2026
        12.04.2026
        05 Weeks
        Deputy Registrar
        09.02.2026
        """
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 50), sample_text)
        pdf_bytes = doc.tobytes()
        doc.close()

        is_valid, record, warnings = self.parser.parse_pdf(pdf_bytes)
        self.assertTrue(is_valid)
        self.assertEqual(record.documentStatus, CalendarStatus.DRAFT)
        self.assertEqual(record.revisionRank, 1)

    def test_parse_pdf_validation_failure_invalid_dates(self):
        sample_text = """
        Faculty of Applied Sciences
        CALENDAR OF DATES
        ACADEMIC YEAR 2024/2025
        FIRST SEMESTER
        Academic Session
        27-09-2026
        03-08-2026
        08 Weeks
        """
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 50), sample_text)
        pdf_bytes = doc.tobytes()
        doc.close()

        is_valid, record, errors = self.parser.parse_pdf(pdf_bytes)
        self.assertFalse(is_valid)
        self.assertIsNone(record)
        self.assertTrue(any("invalid date range" in e for e in errors))

    def test_parse_pdf_missing_academic_year(self):
        sample_text = """
        Faculty of Applied Sciences
        CALENDAR OF DATES
        FIRST SEMESTER
        Academic Session
        03-08-2026
        27-09-2026
        """
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 50), sample_text)
        pdf_bytes = doc.tobytes()
        doc.close()

        is_valid, record, errors = self.parser.parse_pdf(pdf_bytes)
        self.assertFalse(is_valid)
        self.assertIn("Could not identify academic year label from document", errors)
