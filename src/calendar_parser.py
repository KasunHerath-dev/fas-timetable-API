"""PDF parser and validator for FAS WUSL Academic Calendar documents."""

import hashlib
import io
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

import pymupdf

from .calendar_models import (
    AcademicCalendarRecord,
    CalendarActivity,
    CalendarStatus,
    ActivityCategory,
    CalendarValidationStatus,
)
from .config import CALENDAR_PARSER_VERSION

logger = logging.getLogger(__name__)

DATE_REGEX = re.compile(r"(\d{1,2})[-.](\d{1,2})[-.](\d{4})")
ACADEMIC_YEAR_REGEX = re.compile(r"(\d{4})\s*[\/\-]\s*(\d{4})")
DURATION_WEEKS_REGEX = re.compile(r"(\d{1,2})\s*weeks?", re.IGNORECASE)
DURATION_DAYS_REGEX = re.compile(r"(\d{1,2})\s*days?", re.IGNORECASE)


def parse_date_to_iso(date_str: str) -> Optional[str]:
    """Parse date strings in DD-MM-YYYY or DD.MM.YYYY into ISO format YYYY-MM-DD."""
    m = DATE_REGEX.search(date_str)
    if not m:
        return None
    day, month, year = m.groups()
    try:
        dt = datetime(int(year), int(month), int(day))
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


def categorize_activity(title: str) -> ActivityCategory:
    """Classify activity title into normalized official category."""
    tl = title.lower()
    if "academic session" in tl:
        return ActivityCategory.ACADEMIC_SESSION
    elif "mid semester vacation" in tl:
        return ActivityCategory.MID_SEMESTER_VACATION
    elif "study leave" in tl:
        return ActivityCategory.STUDY_LEAVE
    elif "examination" in tl:
        return ActivityCategory.EXAMINATION
    elif "christmas" in tl:
        return ActivityCategory.CHRISTMAS_VACATION
    elif "new year" in tl:
        return ActivityCategory.NEW_YEAR_VACATION
    elif "vacation" in tl:
        return ActivityCategory.VACATION
    return ActivityCategory.OTHER


def calculate_duration_weeks(start_iso: str, end_iso: str) -> Optional[float]:
    """Calculate duration in weeks between inclusive start and end dates."""
    try:
        d1 = datetime.strptime(start_iso, "%Y-%m-%d")
        d2 = datetime.strptime(end_iso, "%Y-%m-%d")
        if d2 < d1:
            return None
        days = (d2 - d1).days + 1
        return round(days / 7.0, 1)
    except Exception:
        return None


class AcademicCalendarParser:
    """Parses digital and scanned academic calendar PDF documents into validated structured records."""

    def __init__(self, parser_version: str = CALENDAR_PARSER_VERSION):
        self.parser_version = parser_version

    def extract_page_text(self, page: pymupdf.Page) -> str:
        """Extract text from a PDF page, falling back to OCR for scanned pages."""
        text = page.get_text()
        if len(text.strip()) > 50:
            return text

        # Scanned page fallback with PyMuPDF OCR
        try:
            tp = page.get_textpage_ocr(dpi=300)
            ocr_text = tp.extractText()
            if len(ocr_text.strip()) > 0:
                logger.debug("Successfully performed OCR on scanned calendar page.")
                return ocr_text
        except Exception as exc:
            logger.warning("OCR failed on calendar page: %s", exc)

        return text

    def parse_pdf(
        self,
        pdf_input: Union[str, Path, bytes],
        source_url: str = "",
        notice_url: str = "",
        notice_title: str = "",
        publication_date: Optional[str] = None,
    ) -> Tuple[bool, Optional[AcademicCalendarRecord], List[str]]:
        """Parse an academic calendar PDF document into an AcademicCalendarRecord.

        Returns:
            Tuple of (is_valid, record, validation_errors_or_warnings)
        """
        # Read bytes and compute SHA-256
        if isinstance(pdf_input, (str, Path)):
            with open(pdf_input, "rb") as f:
                pdf_bytes = f.read()
        else:
            pdf_bytes = pdf_input

        sha256 = hashlib.sha256(pdf_bytes).hexdigest()

        try:
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        except Exception as exc:
            logger.error("Failed to open PDF document: %s", exc)
            return False, None, [f"Corrupt or invalid PDF file: {type(exc).__name__}"]

        if len(doc) == 0:
            return False, None, ["PDF document contains 0 pages"]

        pages_text: List[str] = [self.extract_page_text(p) for p in doc]
        full_combined_text = "\n".join(pages_text)

        # 1. Academic Year
        ay_match = ACADEMIC_YEAR_REGEX.search(full_combined_text)
        if not ay_match:
            return False, None, ["Could not identify academic year label from document"]

        start_year = int(ay_match.group(1))
        end_year = int(ay_match.group(2))
        academic_year = f"{start_year}/{end_year}"

        # 2. Document Title & Status
        first_page = pages_text[0].upper()
        if "DRAFT" in first_page:
            doc_status = CalendarStatus.DRAFT
            doc_title = "DRAFT CALENDAR OF DATES"
            revision = "Draft"
            revision_rank = 1
        elif "REVISED" in first_page:
            doc_status = CalendarStatus.REVISED
            doc_title = "REVISED CALENDAR OF DATES"
            revision = "Revised"
            revision_rank = 3
        else:
            doc_status = CalendarStatus.APPROVED
            doc_title = "CALENDAR OF DATES"
            revision = "Original"
            revision_rank = 2

        # 3. Levels covered
        levels_set = set()
        for page_text in pages_text:
            lvl_m = re.search(r"LEVEL\s*([0-9,\s&]+)", page_text, re.IGNORECASE)
            if lvl_m:
                nums = re.findall(r"\d+", lvl_m.group(1))
                for n in nums:
                    val = int(n)
                    if 1 <= val <= 4:
                        levels_set.add(val)
        levels = sorted(list(levels_set)) if levels_set else [1, 2, 3, 4]

        # 4. Signature / Approval Date
        signature_date: Optional[str] = None
        for page_text in reversed(pages_text):
            # Look for date near Deputy Registrar or signature lines at the end
            lines = [l.strip() for l in page_text.splitlines() if l.strip()]
            for l in reversed(lines[-8:]):
                iso_d = parse_date_to_iso(l)
                if iso_d:
                    signature_date = iso_d
                    break
            if signature_date:
                break

        # 5. Activities and Semesters
        activities: List[CalendarActivity] = []
        semesters_covered: Set[str] = set()
        warnings: List[str] = []

        for p_idx, page_text in enumerate(pages_text):
            lines = [l.strip() for l in page_text.splitlines() if l.strip()]
            current_semester = "Semester I"

            i = 0
            while i < len(lines):
                line = lines[i]

                # Check for semester headers
                if "FIRST SEMESTER" in line.upper() or "FIRST  SEMESTER" in line.upper():
                    current_semester = "Semester I"
                    semesters_covered.add(current_semester)
                    i += 1
                    continue
                elif "SECOND SEMESTER" in line.upper() or "SECOND  SEMESTER" in line.upper():
                    current_semester = "Semester II"
                    semesters_covered.add(current_semester)
                    i += 1
                    continue
                elif any(h in line.upper() for h in [
                    "FROM", "TO", "DURATION", "FACULTY OF", "WAYAMBA UNIVERSITY",
                    "KULIYAPITIYA", "DEGREE PROGRAMMES", "CALENDAR OF DATES",
                    "ACADEMIC YEAR", "DEPUTY REGISTRAR"
                ]):
                    i += 1
                    continue

                # Detect Activity row
                # Line could be the start of an activity title. Look ahead for dates.
                title_parts = [line]
                lookahead = i + 1
                found_dates = False
                d1_iso = None
                d2_iso = None

                while lookahead < len(lines) and lookahead - i <= 4:
                    l_check = lines[lookahead]
                    if DATE_REGEX.search(l_check):
                        # Found start of dates
                        d1_iso = parse_date_to_iso(l_check)
                        if lookahead + 1 < len(lines) and DATE_REGEX.search(lines[lookahead + 1]):
                            d2_iso = parse_date_to_iso(lines[lookahead + 1])
                            found_dates = True
                        break
                    else:
                        # Append to title parts if not a header
                        if not any(h in l_check.upper() for h in ["FIRST SEMESTER", "SECOND SEMESTER", "FROM", "TO"]):
                            title_parts.append(l_check)
                        lookahead += 1

                if found_dates and d1_iso and d2_iso:
                    full_activity_title = " ".join(title_parts).strip()
                    # Clean repeated dots/underscores
                    cleaned_title = re.sub(r"[\.]{2,}", "...", full_activity_title)

                    # Extract duration
                    dur_index = lookahead + 2
                    duration_raw = ""
                    dur_weeks = None

                    if dur_index < len(lines):
                        cand_dur = lines[dur_index]
                        if "week" in cand_dur.lower() or "day" in cand_dur.lower() or cand_dur.isdigit():
                            duration_raw = cand_dur
                            # Check if next line continues duration (e.g. "02 Weeks &" followed by "04 days")
                            if dur_index + 1 < len(lines) and ("day" in lines[dur_index + 1].lower() or "week" in lines[dur_index + 1].lower()):
                                duration_raw += f" {lines[dur_index + 1]}"
                                dur_index += 1

                    # Parse or calculate duration in weeks
                    if duration_raw:
                        wm = DURATION_WEEKS_REGEX.search(duration_raw)
                        dm = DURATION_DAYS_REGEX.search(duration_raw)
                        if wm:
                            weeks_val = float(wm.group(1))
                            if dm:
                                weeks_val += round(float(dm.group(1)) / 7.0, 1)
                            dur_weeks = weeks_val
                        elif duration_raw.strip().isdigit():
                            dur_weeks = float(duration_raw.strip())
                    if dur_weeks is None:
                        dur_weeks = calculate_duration_weeks(d1_iso, d2_iso)

                    # Row validation
                    row_status = CalendarValidationStatus.VALID
                    row_warnings: List[str] = []
                    if d1_iso > d2_iso:
                        row_status = CalendarValidationStatus.INVALID
                        row_warnings.append(f"Start date {d1_iso} is after end date {d2_iso}")

                    category = categorize_activity(cleaned_title)

                    activity_entry = CalendarActivity(
                        activity=cleaned_title,
                        category=category,
                        semester=current_semester,
                        startDate=d1_iso,
                        endDate=d2_iso,
                        durationRaw=duration_raw.strip(),
                        durationWeeks=dur_weeks,
                        validationStatus=row_status,
                        warnings=row_warnings,
                    )
                    activities.append(activity_entry)
                    semesters_covered.add(current_semester)

                    # Advance loop past duration
                    i = dur_index + 1
                    continue

                i += 1

        # Validation Checks
        validation_status = CalendarValidationStatus.VALID
        critical_errors: List[str] = []

        if not activities:
            critical_errors.append("No calendar activities could be extracted from PDF")
            return False, None, critical_errors

        # Check for invalid rows
        for act in activities:
            if act.validationStatus == CalendarValidationStatus.INVALID:
                critical_errors.append(f"Activity '{act.activity}' has invalid date range ({act.startDate} -> {act.endDate})")
            if act.warnings:
                warnings.extend(act.warnings)

        if critical_errors:
            validation_status = CalendarValidationStatus.INVALID
            return False, None, critical_errors
        elif warnings:
            validation_status = CalendarValidationStatus.NEEDS_REVIEW

        # Build stable calendarId
        clean_ay = academic_year.replace("/", "_")
        slug_status = doc_status.value
        calendar_id = f"cal_{clean_ay}_{slug_status}_{sha256[:8]}"

        now_iso = datetime.now().astimezone().isoformat()
        record = AcademicCalendarRecord(
            calendarId=calendar_id,
            academicYear=academic_year,
            academicYearStart=start_year,
            academicYearEnd=end_year,
            documentTitle=doc_title,
            documentStatus=doc_status,
            revision=revision,
            revisionRank=revision_rank,
            levels=levels,
            semesters=sorted(list(semesters_covered)) if semesters_covered else ["Semester I"],
            sourceUrl=source_url,
            noticeUrl=notice_url,
            noticeTitle=notice_title,
            publicationDate=publication_date,
            signatureDate=signature_date,
            sha256=sha256,
            firstSeenAt=now_iso,
            lastSeenAt=now_iso,
            lastValidatedAt=now_iso,
            parserVersion=self.parser_version,
            validationStatus=validation_status,
            warnings=warnings,
            activitiesCount=len(activities),
            activities=activities,
            isCurrent=False,
            isCurrentConfirmed=False,
            selectionReason="",
            revisionHistory=[],
            updatedAt=now_iso,
        )

        return True, record, warnings
