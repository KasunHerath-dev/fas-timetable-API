"""Unit tests for PDF inspector."""

import unittest
import pymupdf

from src.pdf_inspector import parse_pdf_first_page_text, inspect_pdf_bytes


class TestPDFInspector(unittest.TestCase):

    def test_parse_standard_header(self):
        text = """Faculty of Applied Sciences
Wayamba University of Sri Lanka
Kuliyapitiya
B.Sc. (General/Joint Major/Honours) Degree Programme – Academic Year 2024/2025
Level 1 – Semester I
TIME TABLE – (Revised 02)
Time Monday Tuesday
"""
        is_valid, meta, err = parse_pdf_first_page_text(text)
        self.assertTrue(is_valid)
        self.assertIsNone(err)
        self.assertEqual(meta["level"], 1)
        self.assertEqual(meta["academic_year"], "2024/2025")
        self.assertEqual(meta["academic_year_start"], 2024)
        self.assertEqual(meta["semester"], "Semester I")
        self.assertEqual(meta["semester_num"], 1)
        self.assertEqual(meta["revision"], "Revised 02")
        self.assertEqual(meta["revision_rank"], 2)

    def test_parse_roman_numerals(self):
        text = """Faculty of Applied Sciences
Wayamba University of Sri Lanka
B.Sc. Degree Programme – Academic Year 2024/2025
Level III – Semester II
TIME TABLE - (Revised)
"""
        is_valid, meta, err = parse_pdf_first_page_text(text)
        self.assertTrue(is_valid)
        self.assertEqual(meta["level"], 3)
        self.assertEqual(meta["semester"], "Semester II")
        self.assertEqual(meta["semester_num"], 2)
        self.assertEqual(meta["revision"], "Revised")
        self.assertEqual(meta["revision_rank"], 1)

    def test_parse_original_revision(self):
        text = """Faculty of Applied Sciences
Wayamba University of Sri Lanka
B.Sc. Degree Programme – Academic Year 2024/2025
Level 2 – Semester I
TIME TABLE
"""
        is_valid, meta, err = parse_pdf_first_page_text(text)
        self.assertTrue(is_valid)
        self.assertEqual(meta["level"], 2)
        self.assertEqual(meta["revision"], "Original")
        self.assertEqual(meta["revision_rank"], 0)

    def test_parse_re_revised(self):
        text = """Faculty of Applied Sciences
Wayamba University of Sri Lanka
B.Sc. Degree Programme – Academic Year 2023/2024
Level 4 – Semester II
TIME TABLE / Re-Revised
"""
        is_valid, meta, err = parse_pdf_first_page_text(text)
        self.assertTrue(is_valid)
        self.assertEqual(meta["level"], 4)
        self.assertEqual(meta["academic_year"], "2023/2024")
        self.assertEqual(meta["academic_year_start"], 2023)
        self.assertEqual(meta["revision"], "Re-Revised")
        self.assertEqual(meta["revision_rank"], 2)

    def test_ambiguous_levels_reporting(self):
        # Multiple contradictory levels in header with no fallback hint
        text = """Faculty of Applied Sciences
Level 1 and Level 2 Combined Session
No clear single level
"""
        is_valid, meta, err = parse_pdf_first_page_text(text)
        self.assertFalse(is_valid)
        self.assertIn("Ambiguous candidate", err)

    def test_empty_text(self):
        is_valid, meta, err = parse_pdf_first_page_text("   \n\t  ")
        self.assertFalse(is_valid)
        self.assertIn("no readable text", err)

    def test_inspect_pdf_bytes_synthetic(self):
        # Create an in-memory PDF with PyMuPDF
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text(
            (50, 100),
            "Faculty of Applied Sciences\n"
            "Academic Year 2024/2025\n"
            "Level 3 – Semester I\n"
            "TIME TABLE – (Revised)\n"
        )
        pdf_bytes = doc.tobytes()
        doc.close()

        is_valid, meta, err = inspect_pdf_bytes(pdf_bytes)
        self.assertTrue(is_valid)
        self.assertEqual(meta["level"], 3)
        self.assertEqual(meta["academic_year"], "2024/2025")
        self.assertEqual(meta["revision"], "Revised")


if __name__ == "__main__":
    unittest.main()
