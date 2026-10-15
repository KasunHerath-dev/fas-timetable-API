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


# Include API router with /api prefix (for standard and local routes) and root prefix (for serverless environments)
app.include_router(api_router, prefix="/api")
app.include_router(api_router)
