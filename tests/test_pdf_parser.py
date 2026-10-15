"""Unit tests for timetable PDF parser, models, and JSON export."""

import json
import tempfile
import unittest
from pathlib import Path

from src.parser_models import ValidationStatus
from src.timetable_parser import (
    TimetablePDFParser,
    is_lunch_cell,
    normalize_time_str,
    parse_session_chunk,
    split_cell_text,
)


class TestTimetableParser(unittest.TestCase):

    def test_normalize_time_str(self):
        # Morning slots
        self.assertEqual(normalize_time_str("07.30 a.m. - 08.30 a.m."), ("07:30", "08:30"))
        self.assertEqual(normalize_time_str("08.30 a.m. - 09.30 a.m."), ("08:30", "09:30"))
        self.assertEqual(normalize_time_str("10.30 a.m. - 11.30 a.m."), ("10:30", "11:30"))
        self.assertEqual(normalize_time_str("11.30 a.m. - 12.30 p.m."), ("11:30", "12:30"))

        # Noon and lunch
        self.assertEqual(normalize_time_str("12.30 p.m. – 01.30 p.m."), ("12:30", "13:30"))

        # Afternoon and evening slots
        self.assertEqual(normalize_time_str("01.30 p.m. – 02.30 p.m."), ("13:30", "14:30"))
        self.assertEqual(normalize_time_str("02.30 p.m. – 03.30 p.m."), ("14:30", "15:30"))
        self.assertEqual(normalize_time_str("05.30 p.m. – 06.30 p.m."), ("17:30", "18:30"))
        self.assertEqual(normalize_time_str("06.30 p.m. – 07.30 p.m."), ("18:30", "19:30"))

        # Invalid or empty
        self.assertEqual(normalize_time_str(""), (None, None))
        self.assertEqual(normalize_time_str(None), (None, None))
        self.assertEqual(normalize_time_str("Not a time"), (None, None))

    def test_is_lunch_cell(self):
        # Letters forming LUNCH across weekday columns
        self.assertTrue(is_lunch_cell("L"))
        self.assertTrue(is_lunch_cell("U"))
        self.assertTrue(is_lunch_cell("N"))
        self.assertTrue(is_lunch_cell("C"))
        self.assertTrue(is_lunch_cell("H"))

        # Full words
        self.assertTrue(is_lunch_cell("LUNCH"))
        self.assertTrue(is_lunch_cell("L U N C H"))
        self.assertTrue(is_lunch_cell("lunch"))

        # Teaching sessions should NOT be lunch
        self.assertFalse(is_lunch_cell("CMIS 1113 (L)"))
        self.assertFalse(is_lunch_cell("STAT 3112 (T) LR - 09"))
        self.assertFalse(is_lunch_cell("Orientation"))
        self.assertFalse(is_lunch_cell(None))

    def test_split_cell_text(self):
        # Single session
        chunks1 = split_cell_text("CMIS 1113 (L)\nMH")
        self.assertEqual(len(chunks1), 1)

        # Two sessions
        chunks2 = split_cell_text("IMGT 1112 (L)\nLR- 07\nCMIS 1131 (P)\nGp. ll")
        self.assertEqual(len(chunks2), 2)
        self.assertIn("IMGT 1112", chunks2[0])
        self.assertIn("CMIS 1131", chunks2[1])

        # Three sessions
        chunks3 = split_cell_text("CMIS 3134 (L)\nLR - 07\nIMGT 3172 (L)\nLR - 09\nMATH 3114 (L)\nLR - 08")
        self.assertEqual(len(chunks3), 3)

    def test_parse_session_chunk_fields(self):
        raw = "IMGT 1112 (L)\nLR- 07\nCMIS 1131 (P)\nGp. ll"
        session1 = parse_session_chunk(
            chunk="IMGT 1112 (L)\nLR- 07",
            raw_cell=raw,
            day="Monday",
            default_start="08:30",
            default_end="09:30",
        )
        self.assertEqual(session1.day, "Monday")
        self.assertEqual(session1.start_time, "08:30")
        self.assertEqual(session1.end_time, "09:30")
        self.assertEqual(session1.subject_code, "IMGT 1112")
        self.assertEqual(session1.session_type, "Lecture")
        self.assertIsNone(session1.group)
        self.assertEqual(session1.location, "LR- 07")
        self.assertEqual(session1.validation_status, ValidationStatus.VALID)
        self.assertEqual(session1.raw_cell_text, raw)

        session2 = parse_session_chunk(
            chunk="CMIS 1131 (P)\nGp. ll",
            raw_cell=raw,
            day="Monday",
            default_start="08:30",
            default_end="09:30",
        )
        self.assertEqual(session2.subject_code, "CMIS 1131")
        self.assertEqual(session2.session_type, "Practical")
        self.assertEqual(session2.group, "Gp. ll")
        self.assertIsNone(session2.location)
        self.assertEqual(session2.validation_status, ValidationStatus.VALID)

    def test_custom_embedded_time_override(self):
        raw = "CMIS 2113 (P)\nGp. lV\n12.30 p.m. – 2.30 p.m."
        session = parse_session_chunk(
            chunk=raw,
            raw_cell=raw,
            day="Friday",
            default_start="13:30",
            default_end="14:30",
        )
        self.assertEqual(session.subject_code, "CMIS 2113")
        self.assertEqual(session.session_type, "Practical")
        self.assertEqual(session.group, "Gp. lV")
        # Overridden to custom time
        self.assertEqual(session.start_time, "12:30")
        self.assertEqual(session.end_time, "14:30")

    def test_ambiguous_data_review_flagging(self):
        chunk = "ELTN 4+92\nSeminar Room ELTN"
        session = parse_session_chunk(
            chunk=chunk,
            raw_cell=chunk,
            day="Monday",
            default_start="13:30",
            default_end="14:30",
        )
        self.assertEqual(session.validation_status, ValidationStatus.NEEDS_REVIEW)
        self.assertTrue(any("Unusual character" in w for w in session.warnings))

    def test_eltn_lab_location_extraction(self):
        chunk = "ELTN 2112 (P)\nELTN Lab"
        session = parse_session_chunk(
            chunk=chunk,
            raw_cell=chunk,
            day="Tuesday",
            default_start="10:30",
            default_end="11:30",
        )
        self.assertEqual(session.location, "ELTN Lab")
        self.assertEqual(session.subject_code, "ELTN 2112")
        self.assertEqual(session.session_type, "Practical")
        self.assertEqual(session.validation_status, ValidationStatus.VALID)

    def test_math_1112_missing_type_marked_needs_review(self):
        chunk = "MATH 1112"
        session = parse_session_chunk(
            chunk=chunk,
            raw_cell=chunk,
            day="Friday",
            default_start="10:30",
            default_end="11:30",
        )
        self.assertEqual(session.subject_code, "MATH 1112")
        self.assertIsNone(session.session_type)
        self.assertEqual(session.validation_status, ValidationStatus.NEEDS_REVIEW)
        self.assertTrue(any("Missing session type" in w for w in session.warnings))

    def test_mis_4142_prefix_marked_needs_review(self):
        chunk = "MIS 4142 (L)\nLR- 08"
        session = parse_session_chunk(
            chunk=chunk,
            raw_cell=chunk,
            day="Thursday",
            default_start="08:30",
            default_end="09:30",
        )
        self.assertEqual(session.subject_code, "MIS 4142")
        self.assertEqual(session.session_type, "Lecture")
        self.assertEqual(session.location, "LR- 08")
        self.assertEqual(session.validation_status, ValidationStatus.NEEDS_REVIEW)
        self.assertTrue(any("prefix" in w for w in session.warnings))

    def test_dagger_honours_course_preserved(self):
        chunk = "IMGT 3ᵻ34 (L)\nLR- 07"
        session = parse_session_chunk(
            chunk=chunk,
            raw_cell=chunk,
            day="Monday",
            default_start="11:30",
            default_end="12:30",
        )
        self.assertEqual(session.subject_code, "IMGT 3ᵻ34")
        self.assertEqual(session.validation_status, ValidationStatus.NEEDS_REVIEW)
        self.assertTrue(any("Unusual character" in w for w in session.warnings))

    def test_parse_live_pdf_level1(self):
        pdf_path = Path("downloads/level-1_2026-10-05.pdf")
        if not pdf_path.exists():
            self.skipTest("downloads/level-1_2026-10-05.pdf not present")

        parser = TimetablePDFParser()
        parsed = parser.parse_pdf(pdf_path)

        self.assertEqual(parsed.level, 1)
        self.assertEqual(parsed.academic_year, "2024/2025")
        self.assertEqual(parsed.semester, "Semester I")
        self.assertEqual(parsed.revision, "Revised 02")
        self.assertGreater(parsed.total_sessions, 30)

        # Check all days are Monday to Friday
        valid_days = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}
        for s in parsed.sessions:
            self.assertIn(s.day, valid_days)
            self.assertFalse(is_lunch_cell(s.subject_code))

        # Check Page 1 lecturer details are excluded
        subject_codes = [s.subject_code for s in parsed.sessions if s.subject_code]
        self.assertNotIn("Mr. WCC Premarathne", subject_codes)
        self.assertNotIn("Demonstrators", subject_codes)

    def test_parse_live_pdf_level4_lunch_and_reviews(self):
        pdf_path = Path("downloads/level-4_2026-09-10.pdf")
        if not pdf_path.exists():
            self.skipTest("downloads/level-4_2026-09-10.pdf not present")

        parser = TimetablePDFParser()
        parsed = parser.parse_pdf(pdf_path)

        self.assertEqual(parsed.level, 4)
        self.assertGreater(parsed.total_sessions, 50)
        # Verify lunch row was not added as a session
        for s in parsed.sessions:
            self.assertNotIn(s.subject_code, ["L", "U", "N", "C", "H", "LUNCH"])

        # Verify records needing review are flagged
        self.assertGreater(parsed.records_needing_review, 0)

    def test_json_export_and_load(self):
        temp_dir = tempfile.TemporaryDirectory()
        out_dir = Path(temp_dir.name)

        pdf_path = Path("downloads/level-1_2026-10-05.pdf")
        if not pdf_path.exists():
            temp_dir.cleanup()
            self.skipTest("downloads/level-1_2026-10-05.pdf not present")

        parser = TimetablePDFParser(parsed_output_dir=out_dir)
        parsed = parser.parse_pdf(pdf_path)
        out_file = parser.export_parsed_timetable(parsed, output_dir=out_dir)

        self.assertTrue(out_file.exists())
        with open(out_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["level"], 1)
        self.assertEqual(data["academic_year"], "2024/2025")
        self.assertEqual(data["semester"], "Semester I")
        self.assertIn("sessions", data)
        self.assertEqual(len(data["sessions"]), parsed.total_sessions)

        temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
