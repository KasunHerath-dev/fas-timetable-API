"""Deterministic selection policy for the FAS WUSL Academic Calendar."""

import logging
from typing import List, Optional, Tuple, Dict
from .calendar_models import AcademicCalendarRecord, CalendarStatus, CalendarValidationStatus

logger = logging.getLogger(__name__)


class CalendarSelector:
    """Implements verifiable selection logic to determine the active official calendar."""

    @staticmethod
    def select_current_calendar(
        records: List[AcademicCalendarRecord],
    ) -> Tuple[Optional[AcademicCalendarRecord], bool, str]:
        """Select the authoritative current academic calendar from candidate records.

        Selection Policy:
        1. Only consider records passing validation (VALID or NEEDS_REVIEW). Discard INVALID.
        2. Identify candidate academic periods by academicYearStart (e.g. 2024 for '2024/2025').
        3. Within the latest academic year:
           - Prefer official approved/revised documents over drafts.
           - Prefer 'revised' official document over older 'approved' document for the same period.
           - If ties exist with identical status, compare signatureDate / publicationDate.
           - If multiple conflicting records for the target year cannot be reliably resolved,
             retain them and return with is_confirmed=False.
           - If only draft documents exist for the newest academic period, return as unconfirmed.

        Returns:
            Tuple of (selected_record, is_confirmed, selection_reason)
        """
        valid_records = [
            r for r in records
            if r.validationStatus != CalendarValidationStatus.INVALID
        ]

        if not valid_records:
            return None, False, "No valid academic calendar records available"

        # Group by academic year
        records_by_year: Dict[str, List[AcademicCalendarRecord]] = {}
        for r in valid_records:
            records_by_year.setdefault(r.academicYear, []).append(r)

        # Sort academic years by academicYearStart descending
        sorted_years = sorted(
            records_by_year.keys(),
            key=lambda y: records_by_year[y][0].academicYearStart,
            reverse=True,
        )

        latest_year = sorted_years[0]
        year_records = records_by_year[latest_year]

        # Partition by status
        revised_records = [r for r in year_records if r.documentStatus == CalendarStatus.REVISED]
        approved_records = [r for r in year_records if r.documentStatus == CalendarStatus.APPROVED]
        draft_records = [r for r in year_records if r.documentStatus == CalendarStatus.DRAFT]

        # Case 1: Revised documents exist for the latest academic year
        if revised_records:
            # Sort by signatureDate descending, then publicationDate descending
            sorted_revised = sorted(
                revised_records,
                key=lambda r: (r.signatureDate or "", r.publicationDate or "", r.sha256),
                reverse=True,
            )
            # Check for conflict: multiple revised documents for same semester/levels with different hashes and no date distinction
            if len(sorted_revised) > 1 and sorted_revised[0].signatureDate == sorted_revised[1].signatureDate and sorted_revised[0].sha256 != sorted_revised[1].sha256 and sorted_revised[0].semesters == sorted_revised[1].semesters:
                return (
                    sorted_revised[0],
                    False,
                    f"Conflicting revised calendar documents discovered for Academic Year {latest_year}; manual review required",
                )
            selected = sorted_revised[0]
            reason = f"Verified revised official calendar for Academic Year {latest_year}"
            return selected, True, reason

        # Case 2: Approved documents exist
        if approved_records:
            sorted_approved = sorted(
                approved_records,
                key=lambda r: (r.signatureDate or "", r.publicationDate or "", r.sha256),
                reverse=True,
            )
            if len(sorted_approved) > 1 and sorted_approved[0].signatureDate == sorted_approved[1].signatureDate and sorted_approved[0].sha256 != sorted_approved[1].sha256 and sorted_approved[0].semesters == sorted_approved[1].semesters:
                return (
                    sorted_approved[0],
                    False,
                    f"Conflicting approved calendar documents discovered for Academic Year {latest_year}; unconfirmed current selection",
                )
            selected = sorted_approved[0]
            reason = f"Verified official approved calendar for Academic Year {latest_year}"
            return selected, True, reason

        # Case 3: Only Draft documents exist for the latest academic year
        if draft_records:
            # Check if there is an approved calendar in the immediately preceding year
            if len(sorted_years) > 1:
                prev_year = sorted_years[1]
                prev_approved = [
                    r for r in records_by_year[prev_year]
                    if r.documentStatus in (CalendarStatus.APPROVED, CalendarStatus.REVISED)
                ]
                if prev_approved:
                    # Current year only has a draft, while previous year has approved.
                    # We flag selection as unconfirmed.
                    sorted_drafts = sorted(
                        draft_records,
                        key=lambda r: (r.signatureDate or "", r.publicationDate or ""),
                        reverse=True,
                    )
                    selected = sorted_drafts[0]
                    reason = f"Academic Year {latest_year} calendar is marked Draft; official final version unconfirmed"
                    return selected, False, reason

            sorted_drafts = sorted(
                draft_records,
                key=lambda r: (r.signatureDate or "", r.publicationDate or ""),
                reverse=True,
            )
            selected = sorted_drafts[0]
            reason = f"Latest discovered calendar for Academic Year {latest_year} is in Draft status"
            return selected, False, reason

        return None, False, f"Could not determine valid calendar candidate for Academic Year {latest_year}"
