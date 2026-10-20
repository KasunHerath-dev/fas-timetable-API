"""Data models for FAS WUSL Academic Calendar documents, activities, and sync status."""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CalendarStatus(str, Enum):
    """Official status of the academic calendar document."""
    DRAFT = "draft"
    REVISED = "revised"
    APPROVED = "approved"


class ActivityCategory(str, Enum):
    """Normalized category of an academic calendar activity."""
    ACADEMIC_SESSION = "academic_session"
    MID_SEMESTER_VACATION = "mid_semester_vacation"
    STUDY_LEAVE = "study_leave"
    EXAMINATION = "examination"
    CHRISTMAS_VACATION = "christmas_vacation"
    NEW_YEAR_VACATION = "new_year_vacation"
    VACATION = "vacation"
    OTHER = "other"


class CalendarValidationStatus(str, Enum):
    """Validation status for extracted calendar or individual activity."""
    VALID = "VALID"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    INVALID = "INVALID"


class CalendarActivity(BaseModel):
    """Represents a discrete scheduled activity within an academic calendar semester."""
    activity: str = Field(..., description="Original activity title from official document")
    category: ActivityCategory = Field(
        default=ActivityCategory.OTHER,
        description="Normalized activity classification"
    )
    semester: str = Field(..., description="Semester association (e.g. 'Semester I', 'Semester II')")
    startDate: str = Field(..., description="ISO 8601 start date (YYYY-MM-DD)")
    endDate: str = Field(..., description="ISO 8601 end date (YYYY-MM-DD)")
    durationRaw: str = Field(default="", description="Original duration text from document (e.g. '08 Weeks')")
    durationWeeks: Optional[float] = Field(default=None, description="Calculated duration in weeks")
    validationStatus: CalendarValidationStatus = Field(
        default=CalendarValidationStatus.VALID,
        description="Integrity validation status"
    )
    warnings: List[str] = Field(default_factory=list, description="Extraction warnings or ambiguities")


class DiscoveredCalendarLink(BaseModel):
    """Discovered calendar link candidate from the official website."""
    noticeTitle: str
    noticeUrl: str
    publicationDate: Optional[str] = None
    publicationDatetime: Optional[datetime] = None
    pdfUrl: str
    linkText: str = ""


class RevisionHistoryEntry(BaseModel):
    """Metadata entry for historical revisions of a calendar document."""
    sha256: str
    documentTitle: str
    documentStatus: CalendarStatus
    publicationDate: Optional[str] = None
    signatureDate: Optional[str] = None
    sourceUrl: str
    recordedAt: str


class AcademicCalendarRecord(BaseModel):
    """Complete academic calendar document record stored in MongoDB and exposed via API."""
    calendarId: str = Field(..., description="Deterministic stable identifier for the calendar")
    academicYear: str = Field(..., description="Academic year label as published (e.g. '2024/2025')")
    academicYearStart: int = Field(..., description="Gregorian starting year of academic period (e.g. 2024)")
    academicYearEnd: int = Field(..., description="Gregorian ending year of academic period (e.g. 2025)")
    documentTitle: str = Field(..., description="Official document title as published")
    documentStatus: CalendarStatus = Field(default=CalendarStatus.APPROVED, description="Document revision status")
    revision: str = Field(default="Original", description="Revision identifier (e.g. 'Original', 'Revised', 'Draft')")
    revisionRank: int = Field(default=2, description="Numeric rank: draft=1, approved=2, revised=3")
    levels: List[int] = Field(default_factory=lambda: [1, 2, 3, 4], description="Academic levels covered")
    semesters: List[str] = Field(default_factory=list, description="Semesters covered in this document")
    sourceUrl: str = Field(..., description="Direct URL to official PDF document")
    noticeUrl: str = Field(default="", description="URL of notice post containing the document")
    noticeTitle: str = Field(default="", description="Title of the notice post")
    publicationDate: Optional[str] = Field(default=None, description="Notice publication date (YYYY-MM-DD)")
    signatureDate: Optional[str] = Field(default=None, description="Official signature/approval date (YYYY-MM-DD)")
    sha256: str = Field(..., description="SHA-256 hash of PDF document content")
    firstSeenAt: str = Field(..., description="Timestamp when first discovered")
    lastSeenAt: str = Field(..., description="Timestamp when last confirmed on official page")
    lastValidatedAt: str = Field(..., description="Timestamp when successfully validated")
    parserVersion: str = Field(default="1.0.0", description="Parser version that processed the document")
    validationStatus: CalendarValidationStatus = Field(default=CalendarValidationStatus.VALID)
    warnings: List[str] = Field(default_factory=list, description="Document-level warnings")
    activitiesCount: int = Field(default=0, description="Total activities extracted")
    activities: List[CalendarActivity] = Field(default_factory=list, description="Extracted activities")
    isCurrent: bool = Field(default=False, description="Whether this is the currently active calendar")
    isCurrentConfirmed: bool = Field(default=False, description="Whether current status is confirmed with high confidence")
    selectionReason: str = Field(default="", description="Explanation of why this calendar was selected or unconfirmed")
    revisionHistory: List[RevisionHistoryEntry] = Field(default_factory=list, description="Historical revisions")
    updatedAt: str = Field(..., description="Last record update timestamp")


class CalendarSyncStatus(BaseModel):
    """Synchronization health and status tracking model."""
    lastCheckedAt: str
    lastSuccessfulSyncAt: Optional[str] = None
    sourcePageUrl: str
    discoverySuccess: bool
    newerDocumentDiscovered: bool = False
    documentAwaitingValidation: bool = False
    currentCalendarConfirmed: bool = False
    currentCalendarId: Optional[str] = None
    currentAcademicYear: Optional[str] = None
    lastRunFailed: bool = False
    discoveredDocumentsCount: int = 0
    unchangedCount: int = 0
    synchronizedCount: int = 0
    failedCount: int = 0
    lastError: Optional[str] = None
    updatedAt: str
