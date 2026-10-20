"""MongoDB repository for storing and retrieving FAS WUSL Academic Calendar documents."""

import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
import pymongo
from pymongo.collection import Collection
from pymongo.database import Database

from .config import (
    DEFAULT_MONGODB_DATABASE,
    DEFAULT_CALENDARS_COLLECTION,
    DEFAULT_CALENDAR_STATUS_COLLECTION,
    MONGODB_TIMEOUT_MS,
    DEFAULT_CALENDAR_BASE_URL,
)
from .calendar_models import AcademicCalendarRecord, CalendarValidationStatus

logger = logging.getLogger(__name__)

load_dotenv()


class MongoCalendarRepository:
    """Manages persistence of academic calendar records and sync status in MongoDB Atlas."""

    def __init__(
        self,
        uri: Optional[str] = None,
        database_name: Optional[str] = None,
        collection_name: str = DEFAULT_CALENDARS_COLLECTION,
        status_collection_name: str = DEFAULT_CALENDAR_STATUS_COLLECTION,
        client: Optional[pymongo.MongoClient] = None,
    ):
        self.uri = uri or os.getenv("MONGODB_URI")
        self.database_name = database_name or os.getenv("MONGODB_DATABASE", DEFAULT_MONGODB_DATABASE)
        self.collection_name = collection_name
        self.status_collection_name = status_collection_name
        self._external_client = client is not None

        if client is not None:
            self.client = client
        else:
            if not self.uri:
                raise ValueError("MONGODB_URI is required but not configured.")
            self.client = pymongo.MongoClient(
                self.uri,
                serverSelectionTimeoutMS=MONGODB_TIMEOUT_MS,
                connectTimeoutMS=MONGODB_TIMEOUT_MS,
            )

        self.db: Database = self.client[self.database_name]
        self.collection: Collection = self.db[self.collection_name]
        self.status_collection: Collection = self.db[self.status_collection_name]

    def ensure_indexes(self) -> Dict[str, str]:
        """Create indexes on academic_calendars and status collections."""
        indexes = {}
        try:
            cal_idx = self.collection.create_index(
                [("calendarId", pymongo.ASCENDING)],
                unique=True,
                name="idx_calendar_id",
            )
            indexes["calendar_id"] = cal_idx

            ay_idx = self.collection.create_index(
                [("academicYear", pymongo.ASCENDING)],
                name="idx_academic_year",
            )
            indexes["academic_year"] = ay_idx

            current_idx = self.collection.create_index(
                [("isCurrent", pymongo.ASCENDING)],
                name="idx_is_current",
            )
            indexes["is_current"] = current_idx
            return indexes
        except Exception as exc:
            logger.error("Failed to create academic calendar indexes: %s", type(exc).__name__)
            return {}

    def get_calendars(
        self,
        academic_year: Optional[str] = None,
        is_current: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """List academic calendars matching optional filters."""
        query: Dict[str, Any] = {}
        if academic_year:
            normalized_year = academic_year.replace("-", "/")
            query["academicYear"] = normalized_year
        if is_current is not None:
            query["isCurrent"] = is_current

        cursor = self.collection.find(query).sort([("academicYearStart", pymongo.DESCENDING), ("revisionRank", pymongo.DESCENDING)])
        results = []
        for doc in cursor:
            doc["id"] = str(doc.get("_id"))
            del doc["_id"]
            results.append(doc)
        return results

    def get_current_calendar(self) -> Optional[Dict[str, Any]]:
        """Retrieve the currently authoritative academic calendar document."""
        doc = self.collection.find_one({"isCurrent": True})
        if not doc:
            # Fallback: get calendar with highest academicYearStart and highest revisionRank
            doc = self.collection.find_one(
                {"validationStatus": {"$ne": CalendarValidationStatus.INVALID.value}},
                sort=[("academicYearStart", pymongo.DESCENDING), ("revisionRank", pymongo.DESCENDING)],
            )
        if doc:
            doc["id"] = str(doc.get("_id"))
            del doc["_id"]
            return doc
        return None

    def get_calendar_by_academic_year(self, academic_year: str) -> Optional[Dict[str, Any]]:
        """Retrieve the primary calendar for a given academic year."""
        normalized_year = academic_year.replace("-", "/")
        doc = self.collection.find_one(
            {"academicYear": normalized_year},
            sort=[("revisionRank", pymongo.DESCENDING), ("lastValidatedAt", pymongo.DESCENDING)],
        )
        if doc:
            doc["id"] = str(doc.get("_id"))
            del doc["_id"]
            return doc
        return None

    def upsert_calendar(
        self,
        record: AcademicCalendarRecord,
        is_current: bool = False,
        is_confirmed: bool = False,
        selection_reason: str = "",
    ) -> Dict[str, Any]:
        """Idempotently insert or update an academic calendar record, preserving revision history."""
        self.ensure_indexes()
        now_iso = datetime.now(timezone.utc).astimezone().isoformat()
        filter_query = {"calendarId": record.calendarId}

        doc = record.model_dump()
        doc["isCurrent"] = is_current
        doc["isCurrentConfirmed"] = is_confirmed
        doc["selectionReason"] = selection_reason
        doc["updatedAt"] = now_iso

        existing = self.collection.find_one(filter_query)
        if existing:
            # If unchanged SHA-256 and already validated, just update timestamps
            if existing.get("sha256") == record.sha256 and existing.get("validationStatus") == record.validationStatus.value:
                self.collection.update_one(
                    filter_query,
                    {
                        "$set": {
                            "lastSeenAt": now_iso,
                            "isCurrent": is_current,
                            "isCurrentConfirmed": is_confirmed,
                            "selectionReason": selection_reason,
                            "updatedAt": now_iso,
                        }
                    },
                )
                return {"action": "skipped", "calendarId": record.calendarId, "reason": "sha256_match"}

            # Content or validation changed: preserve old version in revisionHistory
            old_history = existing.get("revisionHistory", [])
            old_history.append({
                "sha256": existing.get("sha256"),
                "documentTitle": existing.get("documentTitle"),
                "documentStatus": existing.get("documentStatus"),
                "publicationDate": existing.get("publicationDate"),
                "signatureDate": existing.get("signatureDate"),
                "sourceUrl": existing.get("sourceUrl"),
                "recordedAt": existing.get("updatedAt", now_iso),
            })
            doc["revisionHistory"] = old_history
            doc["firstSeenAt"] = existing.get("firstSeenAt", now_iso)
            self.collection.update_one(filter_query, {"$set": doc})
            action = "updated"
        else:
            self.collection.update_one(filter_query, {"$set": doc}, upsert=True)
            action = "upserted"

        # If this calendar is current, unset isCurrent on all other calendars
        if is_current:
            self.collection.update_many(
                {"calendarId": {"$ne": record.calendarId}},
                {"$set": {"isCurrent": False}},
            )

        return {"action": action, "calendarId": record.calendarId}

    def get_sync_status(self) -> Dict[str, Any]:
        """Retrieve latest academic calendar synchronization status."""
        doc = self.status_collection.find_one({"_id": "global_calendar_status"})
        if doc:
            doc["id"] = str(doc.get("_id"))
            del doc["_id"]
            return doc
        now_iso = datetime.now(timezone.utc).astimezone().isoformat()
        return {
            "lastCheckedAt": now_iso,
            "lastSuccessfulSyncAt": None,
            "sourcePageUrl": DEFAULT_CALENDAR_BASE_URL,
            "discoverySuccess": False,
            "newerDocumentDiscovered": False,
            "documentAwaitingValidation": False,
            "currentCalendarConfirmed": False,
            "currentCalendarId": None,
            "currentAcademicYear": None,
            "lastRunFailed": False,
            "discoveredDocumentsCount": 0,
            "unchangedCount": 0,
            "synchronizedCount": 0,
            "failedCount": 0,
            "lastError": None,
            "updatedAt": now_iso,
        }

    def update_sync_status(self, status_data: Dict[str, Any]) -> None:
        """Update or insert the global academic calendar synchronization status."""
        now_iso = datetime.now(timezone.utc).astimezone().isoformat()
        status_data["updatedAt"] = now_iso
        self.status_collection.update_one(
            {"_id": "global_calendar_status"},
            {"$set": status_data},
            upsert=True,
        )
