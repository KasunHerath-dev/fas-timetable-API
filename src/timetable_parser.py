"""Coordinate-aware timetable parser for FAS WUSL timetable PDFs."""

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import pymupdf

from .config import DEFAULT_PARSED_DIR
from .parser_models import (
    ParsedTimetable,
    TimetableSession,
    ValidationStatus,
)
from .pdf_inspector import inspect_pdf_bytes

logger = logging.getLogger(__name__)

# Subject anchor pattern matching department code + number or known titles
SUBJECT_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])(?:([A-Z]{3,5}\s*[0-9+ᵻ]{3,5})|Business\s+English|Orientation)\b",
    re.IGNORECASE,
)

# Location matching patterns
LOCATION_PATTERNS = [
    r"LR\s*[-–—]?\s*\d{1,2}(?:/\d{1,2})*",
    r"\bMH\b",
    r"Mini\s+Aud[io]torium(?:/LR\s*[\d/]+)?",
    r"Room\s*(?:No\.?)?\s*\d+",
    r"\(?\s*Room\s*\d+\s*\)?",
    r"Interactive\s+Study(?:\s+Centre)?",
    r"Seminar\s+Room(?:\s+ELTN)?",
    r"(?:ELTN\s+|FAS\s+Computer\s+|Computer\s+)?Lab",
]
COMBINED_LOCATION_REGEX = re.compile(
    "|".join(f"(?:{p})" for p in LOCATION_PATTERNS), re.IGNORECASE
)


def normalize_time_str(time_str: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Normalize timetable time slots to 24-hour HH:MM format."""
    if not time_str:
        return None, None

    s = re.sub(r"[\u2013\u2014]", "-", time_str).strip()
    m = re.search(
        r"(\d{1,2})[.:](\d{2})\s*(a\.?m\.?|p\.?m\.?)?\s*-\s*(\d{1,2})[.:](\d{2})\s*(a\.?m\.?|p\.?m\.?)?",
        s,
        re.IGNORECASE,
    )
    if not m:
        return None, None

    h1, m1, ap1, h2, m2, ap2 = m.groups()
    h1, m1, h2, m2 = int(h1), int(m1), int(h2), int(m2)

    ap2_str = ap2.lower().replace(".", "") if ap2 else ""
    ap1_str = ap1.lower().replace(".", "") if ap1 else ""

    if not ap2_str:
        if 7 <= h2 <= 11:
            ap2_str = "am"
        elif h2 == 12 or (1 <= h2 <= 9):
            ap2_str = "pm"

    if not ap1_str:
        if ap2_str == "am":
            ap1_str = "am"
        elif ap2_str == "pm":
            if h1 == 11 or h1 == 12 or h1 >= 7:
                ap1_str = "am" if h1 < 12 else "pm"
            else:
                ap1_str = "pm"

    def to_24(h: int, ap: str) -> int:
        if ap == "am":
            return 0 if h == 12 else h
        elif ap == "pm":
            return 12 if h == 12 else h + 12
        return h

    start_h = to_24(h1, ap1_str)
    end_h = to_24(h2, ap2_str)
    return f"{start_h:02d}:{m1:02d}", f"{end_h:02d}:{m2:02d}"


def is_lunch_cell(text: Optional[str]) -> bool:
    """Check if cell represents lunch break."""
    if not text:
        return False
    c = text.strip()
    return bool(re.match(r"^(?:L|U|N|C|H|LUNCH|L\s*U\s*N\s*C\s*H)$", c, re.IGNORECASE))


def split_cell_text(cell_text: str) -> List[str]:
    """Split multi-session cell text into individual session text chunks."""
    clean = cell_text.strip()
    matches = list(SUBJECT_PATTERN.finditer(clean))
    if not matches:
        return [clean]

    chunks: List[str] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(clean)
        chunk = clean[start:end].strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def parse_session_chunk(
    chunk: str,
    raw_cell: str,
    day: str,
    default_start: str,
    default_end: str,
) -> TimetableSession:
    """Parse a single session text chunk into a TimetableSession model."""
    chunk_clean = chunk.strip()
    warnings: List[str] = []

    # 1. Subject code
    subj_m = SUBJECT_PATTERN.search(chunk_clean)
    subject_code = subj_m.group(0).strip() if subj_m else None
    if subject_code:
        # Standardize multiple spaces: "CMIS  1113" -> "CMIS 1113"
        subject_code = re.sub(r"\s+", " ", subject_code)

    # 2. Session type: (L), (T), (P)
    type_m = re.search(r"\(([LTP])\)|(?<=\s)([LTP])(?=\s|$)", chunk_clean)
    session_type = None
    if type_m:
        st = (type_m.group(1) or type_m.group(2)).upper()
        session_type = {"L": "Lecture", "T": "Tutorial", "P": "Practical"}.get(st, st)

    # 3. Practical group: Gp. I, Gp. ll, etc.
    grp_m = re.search(
        r"(?:Gp\.|Group)\s*([0-9A-Za-z\s&/]+?)(?=\n|LR|MH|Mini|Room|Interactive|Seminar|Lab|$)",
        chunk_clean,
        re.IGNORECASE,
    )
    group = grp_m.group(0).strip() if grp_m else None
    if group:
        group = re.sub(r"\s+", " ", group)

    # 4. Location:
    loc_m = COMBINED_LOCATION_REGEX.search(chunk_clean)
    location = loc_m.group(0).strip() if loc_m else None
    if location:
        location = re.sub(r"\s+", " ", location).strip("() ")

    # 5. Check if chunk has custom embedded time override (e.g. 12.30 p.m. – 2.30 p.m.)
    start_time = default_start
    end_time = default_end
    custom_start, custom_end = normalize_time_str(chunk_clean)
    if custom_start and custom_end:
        start_time = custom_start
        end_time = custom_end

    # 6. Validation status
    status = ValidationStatus.VALID
    if not subject_code:
        status = ValidationStatus.NEEDS_REVIEW
        warnings.append("Missing subject code in session chunk")
    elif "+" in subject_code or "ᵻ" in subject_code:
        status = ValidationStatus.NEEDS_REVIEW
        warnings.append(f"Unusual character in subject code: '{subject_code}'")
    elif subject_code.startswith("MIS "):
        status = ValidationStatus.NEEDS_REVIEW
        warnings.append(f"Non-standard department prefix in subject code: '{subject_code}'")
    elif not session_type and subject_code not in ("Orientation", "Business English"):
        status = ValidationStatus.NEEDS_REVIEW
        warnings.append("Missing session type (L/T/P)")

    return TimetableSession(
        day=day,
        start_time=start_time,
        end_time=end_time,
        subject_code=subject_code,
        session_type=session_type,
        group=group,
        location=location,
        raw_cell_text=raw_cell,
        validation_status=status,
        warnings=warnings,
    )


class TimetablePDFParser:
    """Extracts timetable grid sessions from PDF documents using coordinate-aware parsing."""

    def __init__(self, parsed_output_dir: Path = DEFAULT_PARSED_DIR):
        self.parsed_output_dir = Path(parsed_output_dir)

    def parse_pdf(
        self,
        pdf_path: Path,
        metadata_hint: Optional[Dict[str, Any]] = None,
    ) -> ParsedTimetable:
        """Parse a timetable PDF file and return a structured ParsedTimetable."""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        pdf_bytes = pdf_path.read_bytes()
        sha256_hash = hashlib.sha256(pdf_bytes).hexdigest()

        # Extract level, year, semester, revision from page 0 text
        is_valid, meta, err = inspect_pdf_bytes(pdf_bytes)
        if not is_valid or not meta:
            meta = metadata_hint or {
                "level": 0,
                "academic_year": "Unknown",
                "semester": "Unknown",
                "revision": "Original",
            }

        doc = pymupdf.open(pdf_path)
        try:
            if doc.page_count < 1:
                raise ValueError("PDF contains no pages")

            # Timetable grid is always on Page 0
            page0 = doc[0]
            tabs = page0.find_tables()
            if not tabs.tables:
                raise ValueError(f"No timetable table grid detected on Page 0 of {pdf_path.name}")

            table = tabs.tables[0]
            grid_data = table.extract()

            # Weekday column mapping
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            sessions: List[TimetableSession] = []
            file_warnings: List[str] = []

            # Iterate over rows starting after header (row 0)
            for r_idx in range(1, len(grid_data)):
                row = grid_data[r_idx]
                raw_time = row[0]

                # Special case: merged/None lunch row (Level 4 row 6)
                if not raw_time and any(is_lunch_cell(c) for c in row[1:6]):
                    raw_time = "12.30 p.m. – 01.30 p.m."

                start_t, end_t = normalize_time_str(raw_time)
                if not start_t or not end_t:
                    # If this entire row is lunch or non-time row, skip
                    if all(is_lunch_cell(c) or not c for c in row[1:6]):
                        continue
                    file_warnings.append(f"Row {r_idx}: Could not parse time slot '{raw_time}'")
                    start_t, end_t = "00:00", "00:00"

                # Check weekday columns 1 to 5 (Monday - Friday)
                for c_idx in range(1, min(6, len(row))):
                    cell = row[c_idx]
                    if not cell or not cell.strip():
                        continue

                    # Exclude lunch cells
                    if is_lunch_cell(cell):
                        continue

                    day = days[c_idx - 1]
                    raw_cell_text = cell.strip()

                    # Split cell into individual session chunks
                    chunks = split_cell_text(raw_cell_text)
                    for chunk in chunks:
                        session = parse_session_chunk(
                            chunk=chunk,
                            raw_cell=raw_cell_text,
                            day=day,
                            default_start=start_t,
                            default_end=end_t,
                        )
                        sessions.append(session)

            now_iso = datetime.now(timezone.utc).astimezone().isoformat()
            review_count = sum(
                1 for s in sessions if s.validation_status == ValidationStatus.NEEDS_REVIEW
            )

            parsed = ParsedTimetable(
                level=meta["level"],
                academic_year=meta["academic_year"],
                semester=meta["semester"],
                revision=meta["revision"],
                source_pdf=pdf_path.name,
                source_sha256=sha256_hash,
                extraction_timestamp=now_iso,
                sessions=sessions,
                warnings=file_warnings,
                records_needing_review=review_count,
                total_sessions=len(sessions),
            )
            return parsed
        finally:
            doc.close()

    def export_parsed_timetable(
        self,
        parsed: ParsedTimetable,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Export ParsedTimetable to a JSON file named level-{level}.json."""
        dest_dir = Path(output_dir or self.parsed_output_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        target_file = dest_dir / f"level-{parsed.level}.json"
        data = parsed.model_dump()
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info("Exported parsed timetable for Level %d to %s", parsed.level, target_file)
        return target_file

    def parse_all_downloaded(
        self,
        downloads_dir: Path,
        manifest_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
    ) -> Dict[int, ParsedTimetable]:
        """Parse all timetable PDFs in downloads directory."""
        downloads_dir = Path(downloads_dir)
        manifest_entries: Dict[str, Any] = {}

        if manifest_path and Path(manifest_path).exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    m_data = json.load(f)
                    manifest_entries = m_data.get("levels", {})
            except Exception as exc:
                logger.warning("Could not read manifest for metadata: %s", exc)

        results: Dict[int, ParsedTimetable] = {}
        for pdf_file in sorted(downloads_dir.glob("level-*.pdf")):
            # Match level number from filename
            m = re.match(r"level-(\d+)_", pdf_file.name)
            lvl = int(m.group(1)) if m else 0

            meta_hint = manifest_entries.get(str(lvl))
            parsed = self.parse_pdf(pdf_file, metadata_hint=meta_hint)
            self.export_parsed_timetable(parsed, output_dir=output_dir)
            results[parsed.level] = parsed

        return results
