"""Pydantic data models for parsed timetable sessions and export structures."""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ValidationStatus(str, Enum):
    VALID = "VALID"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class SessionType(str, Enum):
    LECTURE = "Lecture"
    TUTORIAL = "Tutorial"
    PRACTICAL = "Practical"
    OTHER = "Other"


class TimetableSession(BaseModel):
    """Represents a single academic teaching or practical session."""
    day: str
    start_time: str
    end_time: str
    subject_code: Optional[str] = None
    session_type: Optional[str] = None
    group: Optional[str] = None
    location: Optional[str] = None
    raw_cell_text: str
    validation_status: ValidationStatus = ValidationStatus.VALID
    warnings: List[str] = Field(default_factory=list)


class ParsedTimetable(BaseModel):
    """Represents the complete parsed timetable for one academic level."""
    level: int
    academic_year: str
    semester: str
    revision: str
    source_pdf: str
    source_sha256: str
    extraction_timestamp: str
    sessions: List[TimetableSession] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    records_needing_review: int = 0
    total_sessions: int = 0
