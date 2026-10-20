"""FastAPI read-only backend API for FAS WUSL Timetables."""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Path, Depends, status
from fastapi.middleware.cors import CORSMiddleware

from .mongodb_repository import MongoTimetableRepository, MongoRepositoryError

logger = logging.getLogger("fas_api")

app = FastAPI(
    title="FAS WUSL Timetable API",
    description="Read-only API for academic timetables and sessions of the Faculty of Applied Sciences, WUSL.",
    version="1.0.0",
)

import os
from fastapi import APIRouter

# Production & Development CORS configuration
cors_origins_raw = os.getenv("CORS_ORIGINS", "")
if cors_origins_raw.strip():
    allowed_origins = [orig.strip() for orig in cors_origins_raw.split(",") if orig.strip()]
else:
    allowed_origins = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

# Wildcard origin cannot be used with allow_credentials=True according to CORS specifications
if "*" in allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
    )
else:
    cors_origin_regex = os.getenv("CORS_ORIGIN_REGEX", r"^https:\/\/.*\.vercel\.app$")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=cors_origin_regex,
        allow_credentials=True,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
    )

api_router = APIRouter()


_shared_repo: Optional[MongoTimetableRepository] = None


def get_repository() -> MongoTimetableRepository:
    """Dependency provider for MongoTimetableRepository reusing connection pool."""
    global _shared_repo
    if _shared_repo is None:
        try:
            _shared_repo = MongoTimetableRepository()
        except Exception as exc:
            logger.error("Failed to initialize database repository: %s", type(exc).__name__)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable",
            ) from None
    return _shared_repo


@api_router.get("/health", summary="Health check endpoint")
def health_check(repo: MongoTimetableRepository = Depends(get_repository)) -> Dict[str, Any]:
    """Check API and MongoDB connectivity health."""
    now_iso = datetime.now(timezone.utc).astimezone().isoformat()
    db_status = "offline"
    try:
        if repo and repo.ping():
            db_status = "connected"
    except Exception as exc:
        logger.warning("Database health check ping failed: %s", type(exc).__name__)
        db_status = "offline"

    return {
        "status": "ok",
        "database": db_status,
        "timestamp": now_iso,
    }


@api_router.get("/timetables", summary="Get available timetables")
def list_timetables(
    level: Optional[int] = Query(None, ge=1, le=4, description="Filter by academic level (1-4)"),
    repo: MongoTimetableRepository = Depends(get_repository),
) -> List[Dict[str, Any]]:
    """List available timetable records with metadata, publication dates, and revision info."""
    try:
        return repo.get_timetables(level=level)
    except MongoRepositoryError as exc:
        logger.error("Failed to query timetables: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        ) from None


@api_router.get("/timetables/{level}/status", summary="Get session status breakdown for a level")
def get_level_status(
    level: int = Path(..., ge=1, le=4, description="Academic level (1-4)"),
    academicYear: Optional[str] = Query(None, description="Academic year (e.g., 2024/2025)"),
    semester: Optional[str] = Query(None, description="Semester (e.g., Semester I)"),
    repo: MongoTimetableRepository = Depends(get_repository),
) -> Dict[str, Any]:
    """Get total, valid, and needs-review session counts for an academic level."""
    try:
        # Default to latest term if not provided
        if not academicYear or not semester:
            tts = repo.get_timetables(level=level)
            if tts:
                academicYear = academicYear or tts[0].get("academicYear")
                semester = semester or tts[0].get("semester")

        return repo.get_level_status(level=level, academic_year=academicYear, semester=semester)
    except MongoRepositoryError as exc:
        logger.error("Failed to query level status: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        ) from None


@api_router.get("/timetables/{level}/sessions", summary="Get timetable sessions for a level")
def get_level_sessions(
    level: int = Path(..., ge=1, le=4, description="Academic level (1-4)"),
    academicYear: Optional[str] = Query(None, description="Academic year (e.g., 2024/2025)"),
    semester: Optional[str] = Query(None, description="Semester (e.g., Semester I)"),
    day: Optional[str] = Query(
        None,
        pattern="^(Monday|Tuesday|Wednesday|Thursday|Friday)$",
        description="Day of week (Monday-Friday)",
    ),
    subjectCode: Optional[str] = Query(None, description="Filter or search by subject code prefix"),
    repo: MongoTimetableRepository = Depends(get_repository),
) -> Dict[str, Any]:
    """Retrieve schedule sessions for an academic level with optional day and subject filters."""
    try:
        # If academic year or semester not supplied, look up the active/latest timetable metadata
        if not academicYear or not semester:
            tts = repo.get_timetables(level=level)
            if tts:
                academicYear = academicYear or tts[0].get("academicYear")
                semester = semester or tts[0].get("semester")

        sessions = repo.get_sessions(
            level=level,
            academic_year=academicYear,
            semester=semester,
            day=day,
            subject_code=subjectCode,
        )

        return {
            "level": level,
            "academicYear": academicYear,
            "semester": semester,
            "day": day,
            "subjectCode": subjectCode,
            "totalSessions": len(sessions),
            "sessions": sessions,
        }
    except MongoRepositoryError as exc:
        logger.error("Failed to query level sessions: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        ) from None


# =============================================================================
# Academic Calendar API Endpoints
# =============================================================================

def _normalize_semester_param(param: str) -> str:
    """Normalize various semester parameter formats into canonical Semester I or Semester II."""
    p = param.strip().lower().replace("-", " ").replace("_", " ")
    if p in ("1", "i", "sem 1", "sem i", "semester 1", "semester i", "first", "first semester"):
        return "Semester I"
    if p in ("2", "ii", "sem 2", "sem ii", "semester 2", "semester ii", "second", "second semester"):
        return "Semester II"
    return param.strip()


@api_router.get("/academic-calendar", summary="List available academic calendars")
def list_academic_calendars(
    academicYear: Optional[str] = Query(None, description="Filter by academic year (e.g. '2024/2025' or '2024-2025')"),
    doc_status: Optional[str] = Query(None, alias="status", description="Filter by status ('approved', 'revised', 'draft')"),
    repo: MongoTimetableRepository = Depends(get_repository),
) -> List[Dict[str, Any]]:
    """List all available academic calendar documents and their metadata."""
    try:
        calendars = repo.get_academic_calendars(academic_year=academicYear)
        if doc_status:
            s_clean = doc_status.strip().lower()
            calendars = [c for c in calendars if str(c.get("documentStatus", "")).lower() == s_clean]
        return calendars
    except MongoRepositoryError as exc:
        logger.error("Failed to query academic calendars: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        ) from None


@api_router.get("/academic-calendar/current", summary="Get current official academic calendar")
def get_current_academic_calendar(
    repo: MongoTimetableRepository = Depends(get_repository),
) -> Dict[str, Any]:
    """Retrieve the authoritative latest academic calendar with verified status."""
    try:
        calendar = repo.get_current_academic_calendar()
        if not calendar:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No official academic calendar found",
            )
        return calendar
    except HTTPException:
        raise
    except MongoRepositoryError as exc:
        logger.error("Failed to query current academic calendar: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        ) from None


@api_router.get("/academic-calendar/upcoming", summary="Get upcoming academic calendar activities")
def get_upcoming_activities(
    reference_date: Optional[str] = Query(
        None,
        description="Reference date in YYYY-MM-DD format (defaults to current local date)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    limit: int = Query(10, ge=1, le=50, description="Maximum activities to return"),
    academicYear: Optional[str] = Query(None, description="Filter activities by academic year"),
    repo: MongoTimetableRepository = Depends(get_repository),
) -> Dict[str, Any]:
    """Retrieve scheduled activities occurring on or after the reference date."""
    try:
        if reference_date:
            ref_iso = reference_date
        else:
            ref_iso = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")

        # Get relevant calendar
        if academicYear:
            calendar = repo.get_academic_calendar_by_year(academicYear)
        else:
            calendar = repo.get_current_academic_calendar()

        if not calendar:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active calendar found to determine upcoming activities",
            )

        activities = calendar.get("activities", [])
        upcoming: List[Dict[str, Any]] = []

        for act in activities:
            s_date = act.get("startDate", "")
            e_date = act.get("endDate", "")

            if not s_date or not e_date:
                continue

            # Classify status relative to reference date
            if s_date <= ref_iso <= e_date:
                act_status = "ongoing"
            elif s_date > ref_iso:
                act_status = "upcoming"
            else:
                act_status = "completed"

            # Filter out completed activities unless they ended today
            if act_status in ("ongoing", "upcoming"):
                item = dict(act)
                item["academicYear"] = calendar.get("academicYear")
                item["status"] = act_status
                upcoming.append(item)

        # Sort chronologically by start date
        upcoming.sort(key=lambda a: (a.get("startDate", ""), a.get("endDate", "")))
        limited_upcoming = upcoming[:limit]

        return {
            "referenceDate": ref_iso,
            "academicYear": calendar.get("academicYear"),
            "totalUpcoming": len(upcoming),
            "limit": limit,
            "activities": limited_upcoming,
        }
    except HTTPException:
        raise
    except MongoRepositoryError as exc:
        logger.error("Failed to query upcoming calendar activities: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        ) from None


@api_router.get("/academic-calendar/status", summary="Get academic calendar synchronization status")
def get_academic_calendar_status(
    repo: MongoTimetableRepository = Depends(get_repository),
) -> Dict[str, Any]:
    """Retrieve synchronization health, last check timestamp, and confirmation status."""
    try:
        return repo.get_calendar_sync_status()
    except MongoRepositoryError as exc:
        logger.error("Failed to query academic calendar sync status: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        ) from None


@api_router.get("/academic-calendar/{academic_year}", summary="Get calendar for a specific academic year")
def get_academic_calendar_by_year(
    academic_year: str = Path(..., description="Academic year (e.g. '2024-2025' or '2024/2025')"),
    repo: MongoTimetableRepository = Depends(get_repository),
) -> Dict[str, Any]:
    """Retrieve full calendar record for a specific academic year."""
    try:
        calendar = repo.get_academic_calendar_by_year(academic_year)
        if not calendar:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Academic calendar not found for year '{academic_year}'",
            )
        return calendar
    except HTTPException:
        raise
    except MongoRepositoryError as exc:
        logger.error("Failed to query calendar for year %s: %s", academic_year, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        ) from None


@api_router.get(
    "/academic-calendar/{academic_year}/semesters/{semester}",
    summary="Get activities for a specific semester in an academic year",
)
def get_academic_calendar_semester(
    academic_year: str = Path(..., description="Academic year (e.g. '2024-2025' or '2024/2025')"),
    semester: str = Path(..., description="Semester (e.g. 'Semester I', '1', 'semester-1')"),
    repo: MongoTimetableRepository = Depends(get_repository),
) -> Dict[str, Any]:
    """Retrieve schedule activities and date range for a specific semester."""
    try:
        calendar = repo.get_academic_calendar_by_year(academic_year)
        if not calendar:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Academic calendar not found for year '{academic_year}'",
            )

        normalized_target_sem = _normalize_semester_param(semester).lower()
        all_activities = calendar.get("activities", [])

        sem_activities = [
            a for a in all_activities
            if _normalize_semester_param(a.get("semester", "")).lower() == normalized_target_sem
        ]

        if not sem_activities:
            available_sems = list(set(a.get("semester", "") for a in all_activities if a.get("semester")))
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Semester '{semester}' not found in calendar '{academic_year}'. Available semesters: {available_sems}",
            )

        sem_name = sem_activities[0].get("semester", semester)
        start_date = min((a["startDate"] for a in sem_activities if a.get("startDate")), default=None)
        end_date = max((a["endDate"] for a in sem_activities if a.get("endDate")), default=None)

        return {
            "academicYear": calendar.get("academicYear"),
            "semester": sem_name,
            "startDate": start_date,
            "endDate": end_date,
            "totalActivities": len(sem_activities),
            "documentStatus": calendar.get("documentStatus"),
            "sourceUrl": calendar.get("sourceUrl"),
            "activities": sem_activities,
        }
    except HTTPException:
        raise
    except MongoRepositoryError as exc:
        logger.error("Failed to query calendar semester: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        ) from None


# Include API router with /api prefix (for standard and local routes) and root prefix (for serverless environments)
app.include_router(api_router, prefix="/api")
app.include_router(api_router)
