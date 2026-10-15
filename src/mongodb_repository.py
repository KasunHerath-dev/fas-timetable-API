"""MongoDB repository for storing and synchronizing timetable metadata and parsed sessions."""

import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from dotenv import load_dotenv
import pymongo
from pymongo.collection import Collection
from pymongo.database import Database

from .config import (
    DEFAULT_MONGODB_DATABASE,
    DEFAULT_MONGODB_COLLECTION,
    DEFAULT_SESSIONS_COLLECTION,
    MONGODB_TIMEOUT_MS,
)
from .models import ManifestEntry
from .parser_models import ParsedTimetable, TimetableSession

logger = logging.getLogger(__name__)

# Ensure environment variables are loaded
load_dotenv()


class MongoRepositoryError(Exception):
    """Custom exception for MongoDB repository operations."""
    pass


class MongoTimetableRepository:
    """Manages persistence of timetable metadata and sessions in MongoDB Atlas."""

    def __init__(
        self,
        uri: Optional[str] = None,
        database_name: Optional[str] = None,
        collection_name: str = DEFAULT_MONGODB_COLLECTION,
        sessions_collection_name: str = DEFAULT_SESSIONS_COLLECTION,
        client: Optional[pymongo.MongoClient] = None,
    ):
        self.uri = uri or os.getenv("MONGODB_URI")
        self.database_name = database_name or os.getenv("MONGODB_DATABASE", DEFAULT_MONGODB_DATABASE)
        self.collection_name = collection_name
        self.sessions_collection_name = sessions_collection_name
        self._external_client = client is not None

        if client is not None:
            self.client = client
        else:
            if not self.uri:
                raise ValueError("MONGODB_URI is required but not configured.")
            try:
                self.client = pymongo.MongoClient(
                    self.uri,
                    serverSelectionTimeoutMS=MONGODB_TIMEOUT_MS,
                    connectTimeoutMS=MONGODB_TIMEOUT_MS,
                )
            except Exception as exc:
                # Do not expose connection URI in exception or logs
                logger.error("Failed to initialize MongoDB client: %s", type(exc).__name__)
                raise MongoRepositoryError(f"MongoDB connection initialization failed: {type(exc).__name__}") from None

        try:
            self.db: Database = self.client[self.database_name]
            self.collection: Collection = self.db[self.collection_name]
            self.sessions_collection: Collection = self.db[self.sessions_collection_name]
        except Exception as exc:
            logger.error("Failed to access MongoDB database/collection: %s", type(exc).__name__)
            raise MongoRepositoryError(f"Database access failed: {type(exc).__name__}") from None

    def ensure_indexes(self) -> Dict[str, str]:
        """Create unique compound indexes on timetables and timetable_sessions."""
        index_names: Dict[str, str] = {}
        try:
            # 1. Timetables metadata collection index
            tt_index = self.collection.create_index(
                [
                    ("level", pymongo.ASCENDING),
                    ("academicYear", pymongo.ASCENDING),
                    ("semester", pymongo.ASCENDING),
                ],
                unique=True,
                name="idx_level_academicYear_semester",
            )
            index_names["timetables"] = tt_index
            logger.debug("Ensured timetables index: %s", tt_index)

            # 2. Sessions collection compound unique slot index
            sess_index = self.sessions_collection.create_index(
                [
                    ("level", pymongo.ASCENDING),
                    ("academicYear", pymongo.ASCENDING),
                    ("semester", pymongo.ASCENDING),
                    ("day", pymongo.ASCENDING),
                    ("startTime", pymongo.ASCENDING),
                    ("subjectCode", pymongo.ASCENDING),
                    ("group", pymongo.ASCENDING),
                ],
                unique=True,
                name="idx_session_unique_slot",
            )
            index_names["timetable_sessions"] = sess_index
            logger.debug("Ensured sessions index: %s", sess_index)

            # 3. Secondary index on timetableId
            self.sessions_collection.create_index(
                [("timetableId", pymongo.ASCENDING)],
                name="idx_session_timetableId",
            )

            # 4. Secondary index for level/term queries
            self.sessions_collection.create_index(
                [
                    ("level", pymongo.ASCENDING),
                    ("academicYear", pymongo.ASCENDING),
                    ("semester", pymongo.ASCENDING),
                ],
                name="idx_session_level_term",
            )
            return index_names
        except Exception as exc:
            logger.error("Failed to create index in MongoDB: %s", type(exc).__name__)
            raise MongoRepositoryError(f"Index creation failed: {type(exc).__name__}") from None

    def ping(self) -> bool:
        """Ping the MongoDB server to verify connectivity."""
        try:
            self.client.admin.command("ping")
            return True
        except Exception as exc:
            logger.error("MongoDB ping failed: %s", type(exc).__name__)
            raise MongoRepositoryError(f"MongoDB ping failed: {type(exc).__name__}") from None

    @staticmethod
    def entry_to_document(entry: ManifestEntry) -> Dict[str, Any]:
        """Convert a ManifestEntry into the MongoDB document format."""
        now_iso = datetime.now(timezone.utc).astimezone().isoformat()
        return {
            "level": entry.level,
            "academicYear": entry.academic_year,
            "semester": entry.semester,
            "revision": entry.revision,
            "noticeTitle": entry.notice_title,
            "noticeUrl": entry.notice_url,
            "sourcePdfUrl": entry.source_pdf_url,
            "publishedDate": entry.publication_date,
            "downloadedAt": entry.download_timestamp,
            "localPath": entry.local_path,
            "fileSize": entry.file_size,
            "sha256": entry.sha256,
            "updatedAt": now_iso,
        }

    def sync_timetable_entry(self, entry: ManifestEntry) -> Dict[str, Any]:
        """Upsert a single timetable metadata entry. Skips write if SHA-256 hash matches."""
        filter_query = {
            "level": entry.level,
            "academicYear": entry.academic_year,
            "semester": entry.semester,
        }

        try:
            existing = self.collection.find_one(filter_query)
            if existing and existing.get("sha256") == entry.sha256:
                logger.info(
                    "Level %d (%s %s) timetable unchanged (SHA-256 match: %s...); skipping MongoDB write.",
                    entry.level,
                    entry.academic_year,
                    entry.semester,
                    entry.sha256[:8],
                )
                return {
                    "level": entry.level,
                    "action": "skipped",
                    "reason": "sha256_match",
                }

            doc = self.entry_to_document(entry)
            res = self.collection.update_one(filter_query, {"$set": doc}, upsert=True)

            action = "upserted" if res.upserted_id is not None else "updated"
            logger.info(
                "Level %d (%s %s) %s in MongoDB (Revision: %s).",
                entry.level,
                entry.academic_year,
                entry.semester,
                action,
                entry.revision,
            )
            return {
                "level": entry.level,
                "action": action,
                "doc_id": res.upserted_id or (existing.get("_id") if existing else None),
            }
        except Exception as exc:
            logger.error(
                "Error synchronizing Level %d to MongoDB: %s",
                entry.level,
                type(exc).__name__,
            )
            raise MongoRepositoryError(
                f"Failed to synchronize Level {entry.level} to MongoDB: {type(exc).__name__}"
            ) from None

    def sync_all(self, entries: Dict[int, ManifestEntry]) -> Dict[str, Any]:
        """Synchronize all manifest metadata entries to MongoDB."""
        self.ensure_indexes()
        results: Dict[int, Dict[str, Any]] = {}
        counts = {"upserted": 0, "updated": 0, "skipped": 0}

        for lvl, entry in entries.items():
            result = self.sync_timetable_entry(entry)
            results[lvl] = result
            action = result.get("action")
            if action in counts:
                counts[action] += 1

        return {
            "counts": counts,
            "results": results,
        }

    # =========================================================================
    # Parsed Timetable Sessions Operations
    # =========================================================================

    def sync_parsed_timetable_sessions(
        self,
        parsed: ParsedTimetable,
    ) -> Dict[str, Any]:
        """Synchronize individual session records for one parsed timetable into timetable_sessions.

        Uses upsert on (level, academicYear, semester, day, startTime, subjectCode, group)
        and prunes stale sessions for this specific level and academic period.
        """
        self.ensure_indexes()

        # Find parent timetable record ID if available
        tt = self.collection.find_one(
            {
                "level": parsed.level,
                "academicYear": parsed.academic_year,
                "semester": parsed.semester,
            }
        )
        timetable_id = str(tt["_id"]) if (tt and "_id" in tt) else f"lvl_{parsed.level}_{parsed.academic_year}_{parsed.semester}"

        counts = {"upserted": 0, "updated": 0, "skipped": 0, "stale_deleted": 0}
        now_iso = datetime.now(timezone.utc).astimezone().isoformat()

        try:
            for s in parsed.sessions:
                val_status = s.validation_status.value if hasattr(s.validation_status, "value") else str(s.validation_status)

                filter_query = {
                    "level": parsed.level,
                    "academicYear": parsed.academic_year,
                    "semester": parsed.semester,
                    "day": s.day,
                    "startTime": s.start_time,
                    "subjectCode": s.subject_code,
                    "group": s.group,
                }

                doc = {
                    "timetableId": timetable_id,
                    "level": parsed.level,
                    "academicYear": parsed.academic_year,
                    "semester": parsed.semester,
                    "day": s.day,
                    "startTime": s.start_time,
                    "endTime": s.end_time,
                    "subjectCode": s.subject_code,
                    "sessionType": s.session_type,
                    "group": s.group,
                    "location": s.location,
                    "rawCellText": s.raw_cell_text,
                    "validationStatus": val_status,
                    "warnings": s.warnings,
                    "sourcePdfHash": parsed.source_sha256,
                    "updatedAt": now_iso,
                }

                existing = self.sessions_collection.find_one(filter_query)
                if (
                    existing
                    and existing.get("endTime") == s.end_time
                    and existing.get("sessionType") == s.session_type
                    and existing.get("location") == s.location
                    and existing.get("sourcePdfHash") == parsed.source_sha256
                    and existing.get("validationStatus") == val_status
                    and existing.get("warnings") == s.warnings
                ):
                    counts["skipped"] += 1
                else:
                    res = self.sessions_collection.update_one(filter_query, {"$set": doc}, upsert=True)
                    if res.upserted_id is not None:
                        counts["upserted"] += 1
                    else:
                        counts["updated"] += 1

            # Prune stale sessions for this level & academic term that don't match the new PDF hash
            stale_filter = {
                "level": parsed.level,
                "academicYear": parsed.academic_year,
                "semester": parsed.semester,
                "sourcePdfHash": {"$ne": parsed.source_sha256},
            }
            del_res = self.sessions_collection.delete_many(stale_filter)
            counts["stale_deleted"] = del_res.deleted_count

            logger.info(
                "Synced Level %d sessions in MongoDB: %d upserted, %d updated, %d skipped, %d stale deleted.",
                parsed.level,
                counts["upserted"],
                counts["updated"],
                counts["skipped"],
                counts["stale_deleted"],
            )
            return {
                "level": parsed.level,
                "total_sessions": len(parsed.sessions),
                "counts": counts,
            }
        except Exception as exc:
            logger.error("Error syncing sessions for Level %d: %s", parsed.level, type(exc).__name__)
            raise MongoRepositoryError(
                f"Failed to synchronize sessions for Level {parsed.level} to MongoDB: {type(exc).__name__}"
            ) from None

    def sync_all_parsed_sessions(
        self,
        parsed_timetables: Dict[int, ParsedTimetable],
    ) -> Dict[str, Any]:
        """Synchronize all parsed timetables into timetable_sessions collection."""
        results: Dict[int, Any] = {}
        totals = {"upserted": 0, "updated": 0, "skipped": 0, "stale_deleted": 0}

        for lvl, parsed in sorted(parsed_timetables.items()):
            res = self.sync_parsed_timetable_sessions(parsed)
            results[lvl] = res
            for k in totals:
                totals[k] += res["counts"].get(k, 0)

        return {
            "totals": totals,
            "levels": results,
        }

    def sync_level_atomic(
        self,
        entry: ManifestEntry,
        parsed: ParsedTimetable,
    ) -> Dict[str, Any]:
        """Atomically synchronize timetable metadata and parsed sessions.

        Uses a multi-document ACID transaction when supported by the deployment
        (e.g., MongoDB Atlas replica sets) to guarantee that metadata and session
        records are committed atomically. If transactions are unsupported or
        fail to initialize, falls back to safe ordered execution.
        """
        self.ensure_indexes()

        def _execute_sync(session=None):
            meta_filter = {
                "level": entry.level,
                "academicYear": entry.academic_year,
                "semester": entry.semester,
            }
            meta_doc = self.entry_to_document(entry)
            meta_kwargs = {"session": session} if session is not None else {}
            meta_res = self.collection.update_one(meta_filter, {"$set": meta_doc}, upsert=True, **meta_kwargs)
            meta_action = "upserted" if meta_res.upserted_id is not None else "updated"

            tt = self.collection.find_one(meta_filter, **meta_kwargs)
            timetable_id = (
                str(tt["_id"])
                if (tt and "_id" in tt)
                else f"lvl_{parsed.level}_{parsed.academic_year}_{parsed.semester}"
            )

            now_iso = datetime.now(timezone.utc).astimezone().isoformat()
            counts = {"upserted": 0, "updated": 0, "skipped": 0, "stale_deleted": 0}

            for s in parsed.sessions:
                val_status = (
                    s.validation_status.value
                    if hasattr(s.validation_status, "value")
                    else str(s.validation_status)
                )
                sess_filter = {
                    "level": parsed.level,
                    "academicYear": parsed.academic_year,
                    "semester": parsed.semester,
                    "day": s.day,
                    "startTime": s.start_time,
                    "subjectCode": s.subject_code,
                    "group": s.group,
                }
                sess_doc = {
                    "timetableId": timetable_id,
                    "level": parsed.level,
                    "academicYear": parsed.academic_year,
                    "semester": parsed.semester,
                    "day": s.day,
                    "startTime": s.start_time,
                    "endTime": s.end_time,
                    "subjectCode": s.subject_code,
                    "sessionType": s.session_type,
                    "group": s.group,
                    "location": s.location,
                    "rawCellText": s.raw_cell_text,
                    "validationStatus": val_status,
                    "warnings": s.warnings,
                    "sourcePdfHash": parsed.source_sha256,
                    "updatedAt": now_iso,
                }
                existing_sess = self.sessions_collection.find_one(sess_filter, **meta_kwargs)
                if (
                    existing_sess
                    and existing_sess.get("endTime") == s.end_time
                    and existing_sess.get("sessionType") == s.session_type
                    and existing_sess.get("location") == s.location
                    and existing_sess.get("sourcePdfHash") == parsed.source_sha256
                    and existing_sess.get("validationStatus") == val_status
                    and existing_sess.get("warnings") == s.warnings
                ):
                    counts["skipped"] += 1
                else:
                    up_res = self.sessions_collection.update_one(
                        sess_filter, {"$set": sess_doc}, upsert=True, **meta_kwargs
                    )
                    if up_res.upserted_id is not None:
                        counts["upserted"] += 1
                    else:
                        counts["updated"] += 1

            stale_filter = {
                "level": parsed.level,
                "academicYear": parsed.academic_year,
                "semester": parsed.semester,
                "sourcePdfHash": {"$ne": parsed.source_sha256},
            }
            del_res = self.sessions_collection.delete_many(stale_filter, **meta_kwargs)
            counts["stale_deleted"] = del_res.deleted_count

            return {
                "level": parsed.level,
                "metadata_action": meta_action,
                "session_counts": counts,
            }

        # Attempt transaction on deployments supporting it (MongoDB Atlas replica sets)
        if hasattr(self.client, "start_session"):
            try:
                with self.client.start_session() as session:
                    with session.start_transaction():
                        return _execute_sync(session=session)
            except Exception as exc:
                exc_name = type(exc).__name__
                exc_str = str(exc).lower()
                # If transaction failed because the deployment doesn't support replica set transactions or mock without session
                if "notsupported" in exc_str or "unsupported" in exc_str or "transaction" in exc_str or isinstance(exc, (TypeError, AttributeError)):
                    logger.debug("Deployment does not support replica set transactions (%s); using ordered fallback.", exc_name)
                else:
                    logger.error("Transactional synchronization failed for Level %d: %s", parsed.level, exc_name)
                    raise MongoRepositoryError(
                        f"Atomic synchronization failed for Level {parsed.level}: {exc_name}"
                    ) from None

        # Safe fallback ordered execution
        try:
            return _execute_sync(session=None)
        except Exception as exc:
            logger.error("Synchronization failed for Level %d: %s", parsed.level, type(exc).__name__)
            raise MongoRepositoryError(
                f"Failed to synchronize Level {parsed.level} to MongoDB: {type(exc).__name__}"
            ) from None

    # =========================================================================
    # Read Queries for Backend API
    # =========================================================================

    def get_timetables(self, level: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve timetable metadata entries, optionally filtered by level."""
        filter_query: Dict[str, Any] = {}
        if level is not None:
            filter_query["level"] = level

        try:
            cursor = self.collection.find(filter_query)
            if hasattr(cursor, "sort"):
                cursor = cursor.sort([("level", pymongo.ASCENDING), ("publicationDate", pymongo.DESCENDING)])
            docs = []
            for doc in cursor:
                d = dict(doc)
                if "_id" in d:
                    d["id"] = str(d.pop("_id"))
                docs.append(d)
            return docs
        except Exception as exc:
            logger.error("Error retrieving timetables: %s", type(exc).__name__)
            raise MongoRepositoryError(f"Failed to query timetables: {type(exc).__name__}") from None

    def get_sessions(
        self,
        level: int,
        academic_year: Optional[str] = None,
        semester: Optional[str] = None,
        day: Optional[str] = None,
        subject_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve parsed sessions for a level with optional term, day, and subject filters."""
        filter_query: Dict[str, Any] = {"level": level}
        if academic_year:
            filter_query["academicYear"] = academic_year
        if semester:
            filter_query["semester"] = semester
        if day:
            filter_query["day"] = day
        if subject_code:
            filter_query["subjectCode"] = {"$regex": f"^{subject_code.strip()}", "$options": "i"}

        try:
            cursor = self.sessions_collection.find(filter_query)
            if hasattr(cursor, "sort"):
                cursor = cursor.sort([("day", pymongo.ASCENDING), ("startTime", pymongo.ASCENDING)])
            docs = []
            for doc in cursor:
                d = dict(doc)
                if "_id" in d:
                    d["id"] = str(d.pop("_id"))
                docs.append(d)
            return docs
        except Exception as exc:
            logger.error("Error retrieving sessions for Level %d: %s", level, type(exc).__name__)
            raise MongoRepositoryError(f"Failed to query sessions: {type(exc).__name__}") from None

    def get_level_status(
        self,
        level: int,
        academic_year: Optional[str] = None,
        semester: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve session counts and validation breakdown for a level."""
        filter_query: Dict[str, Any] = {"level": level}
        if academic_year:
            filter_query["academicYear"] = academic_year
        if semester:
            filter_query["semester"] = semester

        try:
            cursor = self.sessions_collection.find(filter_query)
            docs = list(cursor)
            total = len(docs)
            valid = sum(1 for d in docs if d.get("validationStatus") == "VALID")
            needs_review = sum(1 for d in docs if d.get("validationStatus") == "NEEDS_REVIEW")

            # Group by session types
            session_types: Dict[str, int] = {}
            for d in docs:
                st = d.get("sessionType") or "Unspecified"
                session_types[st] = session_types.get(st, 0) + 1

            return {
                "level": level,
                "academicYear": academic_year,
                "semester": semester,
                "totalSessions": total,
                "validSessions": valid,
                "needsReviewSessions": needs_review,
                "sessionTypes": session_types,
            }
        except Exception as exc:
            logger.error("Error retrieving status for Level %d: %s", level, type(exc).__name__)
            raise MongoRepositoryError(f"Failed to query level status: {type(exc).__name__}") from None

    def close(self):
        """Cleanly close the MongoDB connection."""
        if not self._external_client and hasattr(self, "client") and self.client:
            try:
                self.client.close()
                logger.debug("Closed MongoDB connection.")
            except Exception as exc:
                logger.warning("Error closing MongoDB connection: %s", type(exc).__name__)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
