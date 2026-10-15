"""Unit tests for timetable candidate selector."""

import unittest
from datetime import datetime
from src.models import TimetableCandidate
from src.selector import TimetableSelector


class TestTimetableSelector(unittest.TestCase):

    def _make_candidate(
        self,
        level: int,
        year: str,
        year_start: int,
        semester: str,
        sem_num: int,
        revision: str,
        revision_rank: int,
        date_str: str,
        filename: str,
        notice_title: str = "Notice",
    ) -> TimetableCandidate:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return TimetableCandidate(
            level=level,
            academic_year=year,
            academic_year_start=year_start,
            semester=semester,
            semester_num=sem_num,
            revision=revision,
            revision_rank=revision_rank,
            pdf_url=f"https://fas.wyb.ac.lk/wp-content/uploads/2026/{filename}",
            notice_url="https://fas.wyb.ac.lk/notice-1/",
            notice_title=notice_title,
            publication_date=date_str,
            publication_datetime=dt,
            is_valid=True,
        )

    def test_independent_level_selection_and_newer_revisions(self):
        # Scenario reflecting actual FAS WUSL situation:
        # Notice 1 (Oct 5, 2026): Revised 02 for Level 1 only
        # Notice 2 (Sep 10, 2026): Revised for Levels 1, 2, 3, 4
        # Notice 3 (Jul 30, 2026): Original for Levels 1, 2, 3, 4
        # Notice 4 (Mar 20, 2026): Older year 2023/2024 Sem II for Levels 1, 2, 3, 4
        candidates = [
            # Notice 1
            self._make_candidate(1, "2024/2025", 2024, "Semester I", 1, "Revised 02", 2, "2026-10-05", "Level-1-Revesed-2.pdf", "Notice 1"),
            # Notice 2
            self._make_candidate(1, "2024/2025", 2024, "Semester I", 1, "Revised", 1, "2026-09-10", "Level-13.pdf", "Notice 2"),
            self._make_candidate(2, "2024/2025", 2024, "Semester I", 1, "Revised", 1, "2026-09-10", "Level-23.pdf", "Notice 2"),
            self._make_candidate(3, "2024/2025", 2024, "Semester I", 1, "Revised", 1, "2026-09-10", "Level-34.pdf", "Notice 2"),
            self._make_candidate(4, "2024/2025", 2024, "Semester I", 1, "Revised", 1, "2026-09-10", "Level-45.pdf", "Notice 2"),
            # Notice 3
            self._make_candidate(1, "2024/2025", 2024, "Semester I", 1, "Original", 0, "2026-07-30", "Level-1-10.pdf", "Notice 3"),
            self._make_candidate(2, "2024/2025", 2024, "Semester I", 1, "Original", 0, "2026-07-30", "Level-2-8.pdf", "Notice 3"),
            self._make_candidate(3, "2024/2025", 2024, "Semester I", 1, "Original", 0, "2026-07-30", "Level-3-12.pdf", "Notice 3"),
            self._make_candidate(4, "2024/2025", 2024, "Semester I", 1, "Original", 0, "2026-07-30", "Level-4-14.pdf", "Notice 3"),
            # Notice 4 (Older Academic Year)
            self._make_candidate(1, "2023/2024", 2023, "Semester II", 2, "Re-Revised", 2, "2026-03-20", "Level-110.pdf", "Notice 4"),
            self._make_candidate(2, "2023/2024", 2023, "Semester II", 2, "Re-Revised", 2, "2026-03-20", "Level-210.pdf", "Notice 4"),
            self._make_candidate(3, "2023/2024", 2023, "Semester II", 2, "Re-Revised", 2, "2026-03-20", "Level-3-new1.pdf", "Notice 4"),
            self._make_candidate(4, "2023/2024", 2023, "Semester II", 2, "Re-Revised", 2, "2026-03-20", "Level-410.pdf", "Notice 4"),
        ]

        selected, unselected = TimetableSelector.select_best_candidates(candidates)

        self.assertEqual(len(selected), 4)
        self.assertEqual(len(unselected), 0)

        # Level 1 should be from Notice 1 (Oct 5, Revised 02)
        self.assertEqual(selected[1].pdf_url.split("/")[-1], "Level-1-Revesed-2.pdf")
        self.assertEqual(selected[1].publication_date, "2026-10-05")
        self.assertEqual(selected[1].revision, "Revised 02")

        # Level 2 should be from Notice 2 (Sep 10, Revised)
        self.assertEqual(selected[2].pdf_url.split("/")[-1], "Level-23.pdf")
        self.assertEqual(selected[2].publication_date, "2026-09-10")

        # Level 3 should be from Notice 2 (Sep 10, Revised)
        self.assertEqual(selected[3].pdf_url.split("/")[-1], "Level-34.pdf")
        self.assertEqual(selected[3].publication_date, "2026-09-10")

        # Level 4 should be from Notice 2 (Sep 10, Revised)
        self.assertEqual(selected[4].pdf_url.split("/")[-1], "Level-45.pdf")
        self.assertEqual(selected[4].publication_date, "2026-09-10")

        # All selected should be from 2024/2025 Semester I, none from 2023/2024
        for lvl in (1, 2, 3, 4):
            self.assertEqual(selected[lvl].academic_year, "2024/2025")
            self.assertEqual(selected[lvl].semester, "Semester I")

    def test_missing_level_reporting(self):
        # Only Level 1 and 2 present
        candidates = [
            self._make_candidate(1, "2024/2025", 2024, "Semester I", 1, "Revised", 1, "2026-09-10", "Level-1.pdf"),
            self._make_candidate(2, "2024/2025", 2024, "Semester I", 1, "Revised", 1, "2026-09-10", "Level-2.pdf"),
        ]
        selected, unselected = TimetableSelector.select_best_candidates(candidates)
        self.assertIn(1, selected)
        self.assertIn(2, selected)
        self.assertNotIn(3, selected)
        self.assertNotIn(4, selected)
        self.assertIn(3, unselected)
        self.assertIn(4, unselected)


if __name__ == "__main__":
    unittest.main()
