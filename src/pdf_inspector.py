"""PDF inspection and metadata extraction using PyMuPDF."""

import logging
import re
from typing import Optional, Dict, Any, Tuple
import pymupdf

logger = logging.getLogger(__name__)


def parse_pdf_first_page_text(
    text: str,
    notice_title: str = "",
    fallback_hint: str = "",
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """Parse text from the first page of a timetable PDF.

    Returns:
        (is_valid, metadata_dict, error_message)
    """
    if not text or not text.strip():
        return False, None, "PDF first page has no readable text"

    # Clean text
    clean_text = text.strip()
    header_area = clean_text[:800]

    # --- 1. Identify Academic Level ---
    level: Optional[int] = None

    # High-confidence pattern: "Level X – Semester Y" or "Level X Semester Y"
    header_match = re.search(
        r"\bLevel\s*0?([1-4])\s*[-–—:]?\s*Semester", header_area, re.IGNORECASE
    )
    if header_match:
        level = int(header_match.group(1))
    else:
        # Roman numeral pattern: "Level II – Semester"
        roman_header = re.search(
            r"\bLevel\s*(IV|III|II|I)\s*[-–—:]?\s*Semester", header_area, re.IGNORECASE
        )
        if roman_header:
            roman_map = {"I": 1, "II": 2, "III": 3, "IV": 4}
            level = roman_map.get(roman_header.group(1).upper())

    # Fallback to general "Level X" in header area
    if level is None:
        matches = re.findall(r"\bLevel\s*0?([1-4])\b", header_area, re.IGNORECASE)
        unique_matches = sorted(list(set(int(m) for m in matches)))
        if len(unique_matches) == 1:
            level = unique_matches[0]
        elif len(unique_matches) > 1:
            # Ambiguous: multiple levels in header area
            # Check if fallback_hint (e.g. from link text "Level 01") resolves it
            hint_match = re.search(r"\bLevel\s*0?([1-4])\b", fallback_hint, re.IGNORECASE)
            if hint_match and int(hint_match.group(1)) in unique_matches:
                level = int(hint_match.group(1))
            else:
                return (
                    False,
                    None,
                    f"Ambiguous candidate: multiple levels found in header ({unique_matches})",
                )

    if level is None:
        # Check Roman numerals in header
        roman_matches = re.findall(r"\bLevel\s*(IV|III|II|I)\b", header_area, re.IGNORECASE)
        roman_map = {"I": 1, "II": 2, "III": 3, "IV": 4}
        unique_romans = sorted(list(set(roman_map[r.upper()] for r in roman_matches if r.upper() in roman_map)))
        if len(unique_romans) == 1:
            level = unique_romans[0]
        elif len(unique_romans) > 1:
            return (
                False,
                None,
                f"Ambiguous candidate: multiple roman levels found ({unique_romans})",
            )

    if level is None:
        return False, None, "Could not reliably determine academic level from PDF text"

    # --- 2. Identify Academic Year ---
    year_str = "Unknown"
    year_start = 0
    year_match = re.search(r"Academic\s+Year\s*(\d{4}\s*/\s*\d{4})", header_area, re.IGNORECASE)
    if not year_match:
        # Fallback to notice title
        year_match = re.search(r"Academic\s+Year\s*(\d{4}\s*/\s*\d{4})", notice_title, re.IGNORECASE)

    if year_match:
        year_str = re.sub(r"\s+", "", year_match.group(1))
        try:
            year_start = int(year_str.split("/")[0])
        except (ValueError, IndexError):
            year_start = 0

    # --- 3. Identify Semester ---
    sem_str = "Semester I"
    sem_num = 1
    sem_match = re.search(r"Semester\s*(I{1,2}|IV|V|1|2)\b", header_area, re.IGNORECASE)
    if not sem_match:
        sem_match = re.search(r"Semester\s*(I{1,2}|IV|V|1|2)\b", notice_title, re.IGNORECASE)

    if sem_match:
        raw_sem = sem_match.group(1).upper()
        if raw_sem in ("II", "2"):
            sem_str = "Semester II"
            sem_num = 2
        else:
            sem_str = "Semester I"
            sem_num = 1

    # --- 4. Identify Revision ---
    rev_str = "Original"
    rev_rank = 0

    combined = (notice_title + " " + header_area).replace("-", " ")
    if re.search(r"\bRe\s*Re\s*Revised\b", combined, re.IGNORECASE):
        rev_str = "Re-Re-Revised"
        rev_rank = 3
    elif re.search(r"\bRe\s*Revised\b", combined, re.IGNORECASE):
        rev_str = "Re-Revised"
        rev_rank = 2
    else:
        m = re.search(r"\bRevised\s*0?([1-9]\d*)\b", combined, re.IGNORECASE)
        if m:
            rev_str = f"Revised {int(m.group(1)):02d}"
            rev_rank = int(m.group(1))
        elif re.search(r"\bRevised\b", combined, re.IGNORECASE):
            rev_str = "Revised"
            rev_rank = 1

    metadata = {
        "level": level,
        "academic_year": year_str,
        "academic_year_start": year_start,
        "semester": sem_str,
        "semester_num": sem_num,
        "revision": rev_str,
        "revision_rank": rev_rank,
    }
    return True, metadata, None


def inspect_pdf_bytes(
    pdf_bytes: bytes,
    notice_title: str = "",
    fallback_hint: str = "",
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """Validate PDF bytes and extract metadata from the first page."""
    if not pdf_bytes:
        return False, None, "Empty PDF data received"

    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        return False, None, f"Failed to parse PDF document: {exc}"

    try:
        if doc.page_count < 1:
            return False, None, "PDF has 0 pages"

        first_page = doc[0]
        text = first_page.get_text()
        return parse_pdf_first_page_text(
            text, notice_title=notice_title, fallback_hint=fallback_hint
        )
    finally:
        doc.close()
