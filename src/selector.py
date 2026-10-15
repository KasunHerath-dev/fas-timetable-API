"""Selection logic to pick the newest valid timetable independently for each level."""

import logging
from typing import List, Dict, Tuple, Optional
from .models import TimetableCandidate

logger = logging.getLogger(__name__)


class TimetableSelector:
    """Selects the latest valid timetable for each academic level (1, 2, 3, 4)."""

    @staticmethod
    def determine_target_academic_term(
        candidates: List[TimetableCandidate],
    ) -> Optional[Tuple[int, int, str, str]]:
        """Determine the newest active academic term (year_start, semester_num, year_str, sem_str)."""
        valid_candidates = [c for c in candidates if c.is_valid and c.academic_year_start > 0]
        if not valid_candidates:
            return None

        # Sort terms by year_start, then semester_num
        sorted_by_term = sorted(
            valid_candidates,
            key=lambda c: (c.academic_year_start, c.semester_num),
            reverse=True,
        )
        best = sorted_by_term[0]
        return (
            best.academic_year_start,
            best.semester_num,
            best.academic_year,
            best.semester,
        )

    @classmethod
    def select_best_candidates(
        cls,
        candidates: List[TimetableCandidate],
        target_levels: Tuple[int, ...] = (1, 2, 3, 4),
    ) -> Tuple[Dict[int, TimetableCandidate], Dict[int, str]]:
        """Select the best candidate for each level independently.

        Returns:
            (selected_dict, unselected_reasons_dict)
        """
        valid_candidates = [c for c in candidates if c.is_valid and c.level in target_levels]

        if not valid_candidates:
            logger.warning("No valid candidates found across any level.")
            reasons = {lvl: "No valid candidates discovered" for lvl in target_levels}
            return {}, reasons

        # Target academic term
        term_info = cls.determine_target_academic_term(valid_candidates)
        if not term_info:
            reasons = {lvl: "Could not determine target academic term" for lvl in target_levels}
            return {}, reasons

        target_year_start, target_sem_num, target_year_str, target_sem_str = term_info
        logger.info(
            "Target academic term identified as: %s %s", target_year_str, target_sem_str
        )

        selected: Dict[int, TimetableCandidate] = {}
        unselected_reasons: Dict[int, str] = {}

        for lvl in target_levels:
            # Filter candidates for this level within the target term
            lvl_candidates = [
                c for c in valid_candidates
                if c.level == lvl
                and c.academic_year_start == target_year_start
                and c.semester_num == target_sem_num
            ]

            if not lvl_candidates:
                msg = (
                    f"No valid timetable found for Level {lvl} in "
                    f"Academic Year {target_year_str} {target_sem_str}"
                )
                logger.warning(msg)
                unselected_reasons[lvl] = msg
                continue

            # Sort by publication date (descending), then revision rank (descending)
            lvl_candidates.sort(
                key=lambda c: (c.publication_datetime, c.revision_rank),
                reverse=True,
            )

            chosen = lvl_candidates[0]
            selected[lvl] = chosen
            logger.info(
                "Selected Level %d: %s (Published: %s, Revision: %s, Notice: %s)",
                lvl,
                chosen.pdf_url.split("/")[-1],
                chosen.publication_date,
                chosen.revision,
                chosen.notice_title,
            )

        return selected, unselected_reasons
