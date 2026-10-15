"""Data models for timetable discovery, candidate selection, and manifest."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class PDFLinkInfo:
    url: str
    text: str = ""


@dataclass
class Notice:
    title: str
    url: str
    publication_date: str  # YYYY-MM-DD
    publication_datetime: datetime
    pdf_links: List[PDFLinkInfo] = field(default_factory=list)


@dataclass
class TimetableCandidate:
    level: int
    academic_year: str
    academic_year_start: int
    semester: str
    semester_num: int
    revision: str
    revision_rank: int
    pdf_url: str
    notice_url: str
    notice_title: str
    publication_date: str
    publication_datetime: datetime
    pdf_bytes: Optional[bytes] = None
    is_valid: bool = True
    validation_error: Optional[str] = None

    def sort_key(self):
        """Sort key prioritizing latest academic year, semester, publication date, revision."""
        return (
            self.academic_year_start,
            self.semester_num,
            self.publication_datetime,
            self.revision_rank,
        )


@dataclass
class ManifestEntry:
    level: int
    source_pdf_url: str
    notice_url: str
    notice_title: str
    publication_date: str
    academic_year: str
    semester: str
    revision: str
    download_timestamp: str
    local_path: Optional[str] = None
    file_size: int = 0
    sha256: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
