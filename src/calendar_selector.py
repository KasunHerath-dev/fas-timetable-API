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

        # Sort academic periods by recency:
        # academicYearStart descending, then highest publication date, then highest signature date
        def year_sort_key(year: str):
            recs = records_by_year[year]
            ay_start = recs[0].academicYearStart
            max_pub = max((r.publicationDate or "" for r in recs), default="")
            max_sig = max((r.signatureDate or "" for r in recs), default="")
            return (ay_start, max_pub, max_sig)

        sorted_years = sorted(records_by_year.keys(), key=year_sort_key, reverse=True)
        latest_year = sorted_years[0]
        year_records = records_by_year[latest_year]

        # Partition by status within the latest academic period
        revised_records = [r for r in year_records if r.documentStatus == CalendarStatus.REVISED]
        approved_records = [r for r in year_records if r.documentStatus == CalendarStatus.APPROVED]
        draft_records = [r for r in year_records if r.documentStatus == CalendarStatus.DRAFT]
        unknown_records = [r for r in year_records if r.documentStatus == CalendarStatus.UNKNOWN]

        # Case 1: Revised documents exist for the latest academic year
        if revised_records:
            sorted_revised = sorted(
                revised_records,
                key=lambda r: (r.publicationDate or "", r.signatureDate or "", r.sha256),
                reverse=True,
            )
            if (
                len(sorted_revised) > 1
                and sorted_revised[0].signatureDate == sorted_revised[1].signatureDate
                and sorted_revised[0].sha256 != sorted_revised[1].sha256
                and sorted_revised[0].semesters == sorted_revised[1].semesters
            ):
                return (
                    sorted_revised[0],
                    False,
                    f"Conflicting revised calendar documents discovered for Academic Year {latest_year}; manual review required",
                )
            selected = sorted_revised[0]
            reason = f"Verified revised official calendar for Academic Year {latest_year}"
            return selected, True, reason

        # Case 2: Approved documents exist for the latest academic year
        if approved_records:
            sorted_approved = sorted(
                approved_records,
                key=lambda r: (r.publicationDate or "", r.signatureDate or "", r.sha256),
                reverse=True,
            )
            if (
                len(sorted_approved) > 1
                and sorted_approved[0].signatureDate == sorted_approved[1].signatureDate
                and sorted_approved[0].sha256 != sorted_approved[1].sha256
                and sorted_approved[0].semesters == sorted_approved[1].semesters
            ):
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
            sorted_drafts = sorted(
                draft_records,
                key=lambda r: (r.publicationDate or "", r.signatureDate or "", r.sha256),
                reverse=True,
            )
            selected = sorted_drafts[0]
            reason = f"Academic Year {latest_year} calendar is marked Draft; official final version unconfirmed"
            return selected, False, reason

        # Case 4: Only Unknown status documents exist for the latest academic year
        if unknown_records:
            sorted_unknown = sorted(
                unknown_records,
                key=lambda r: (r.publicationDate or "", r.signatureDate or "", r.sha256),
                reverse=True,
            )
            selected = sorted_unknown[0]
            reason = f"Academic Year {latest_year} calendar approval status cannot be established from source"
            return selected, False, reason

        # Fallback for unexpected status
        sorted_any = sorted(
            year_records,
            key=lambda r: (r.publicationDate or "", r.signatureDate or ""),
            reverse=True,
        )
        return sorted_any[0], False, f"Selected calendar candidate for Academic Year {latest_year} with unconfirmed status"
