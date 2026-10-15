"""Safe daily production worker for FAS WUSL Timetable synchronization.

Performs automated discovery, SHA-256 change detection, temporary PDF inspection,
coordinate-aware parsing, rigorous pre-sync validation, scoped MongoDB Atlas
synchronization, and guaranteed temporary artifact cleanup.
"""

import argparse
import hashlib
import logging
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set

from .config import (
    DEFAULT_BASE_URL,
    DEFAULT_MAX_PAGES,
    DEFAULT_MONGODB_DATABASE,
)
from .downloader import TimetableDownloader, compute_sha256
from .models import TimetableCandidate, ManifestEntry
from .mongodb_repository import MongoTimetableRepository, MongoRepositoryError
from .parser_models import ParsedTimetable, TimetableSession, ValidationStatus
from .pdf_inspector import inspect_pdf_bytes
from .scraper import TimetableScraper
from .selector import TimetableSelector
from .timetable_parser import TimetablePDFParser

logger = logging.getLogger("fas_worker")


def setup_worker_logging(verbose: bool = False):
    """Setup console logging with standard format."""
    level = logging.DEBUG if verbose else logging.INFO
    format_str = "%(asctime)s [%(levelname)s] %(message)s"
    logging.basicConfig(level=level, format=format_str, datefmt="%Y-%m-%d %H:%M:%S")


def deduplicate_identical_sessions(
    sessions: List[TimetableSession],
) -> Tuple[List[TimetableSession], int]:
    """Deduplicate sessions that have identical slot keys and identical attributes."""
    unique_sessions: List[TimetableSession] = []
    seen: Set[Tuple[str, str, str, Optional[str], Optional[str], Optional[str], Optional[str]]] = set()
    dedup_count = 0

    for s in sessions:
        key = (
            s.day,
            s.start_time,
            s.end_time,
            s.subject_code,
            s.session_type,
            s.group,
            s.location,
        )
        if key in seen:
            dedup_count += 1
            continue
        seen.add(key)
        unique_sessions.append(s)

    return unique_sessions, dedup_count


def validate_parsed_timetable(
    parsed: ParsedTimetable,
    min_sessions: int = 1,
) -> Tuple[bool, List[str]]:
    """Validate parsed timetable candidate data before modifying production records.

    Checks:
    - Level in (1, 2, 3, 4)
    - Valid non-empty academic_year and semester
    - Valid 64-char hex SHA-256 source hash
    - Non-empty sessions list and minimum session count threshold
    - Required session fields (day, start_time, end_time, raw_cell_text, validation_status)
    - Valid 24-hour time ranges (start_time < end_time, non-zero unparseable slot)
    - Valid weekdays (Monday through Friday)
    - Conflicting duplicate slot keys (same day, startTime, subjectCode, group)
    """
    errors: List[str] = []

    if parsed.level not in (1, 2, 3, 4):
        errors.append(f"Invalid academic level: {parsed.level}")

    if not parsed.academic_year or parsed.academic_year == "Unknown":
        errors.append("Invalid or missing academic year")

    if not parsed.semester or parsed.semester == "Unknown":
        errors.append("Invalid or missing semester")

    if not parsed.source_sha256 or len(parsed.source_sha256) != 64:
        errors.append("Invalid or missing source SHA-256 hash")

    if len(parsed.sessions) < min_sessions:
        errors.append(
            f"Insufficient session count: found {len(parsed.sessions)}, expected at least {min_sessions}. "
            "Possible PDF table extraction failure."
        )
        return False, errors

    valid_days = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}
    time_regex = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
    seen_slots: Dict[Tuple[str, str, Optional[str], Optional[str]], int] = {}

    for idx, s in enumerate(parsed.sessions):
        # 1. Weekday validation
        if s.day not in valid_days:
            errors.append(f"Session {idx}: Invalid weekday '{s.day}'")

        # 2. Time format validation
        if not s.start_time or not time_regex.match(s.start_time):
            errors.append(f"Session {idx}: Invalid start time '{s.start_time}'")
        if not s.end_time or not time_regex.match(s.end_time):
            errors.append(f"Session {idx}: Invalid end time '{s.end_time}'")

        # 3. Time logic validation
        if s.start_time == "00:00" and s.end_time == "00:00":
            errors.append(f"Session {idx}: Unresolved zero time slot 00:00-00:00 (parser failure)")
        elif s.start_time and s.end_time and s.start_time >= s.end_time:
            errors.append(f"Session {idx}: Start time '{s.start_time}' must precede end time '{s.end_time}'")

        # 4. Raw text presence
        if not s.raw_cell_text or not s.raw_cell_text.strip():
            errors.append(f"Session {idx}: Missing raw cell text")

        # 5. Validation status enum
        if s.validation_status not in (ValidationStatus.VALID, ValidationStatus.NEEDS_REVIEW):
            errors.append(f"Session {idx}: Unknown validation status '{s.validation_status}'")

        # 6. Check conflicting duplicate slot keys
        slot_key = (s.day, s.start_time, s.subject_code, s.group)
        if slot_key in seen_slots:
            first_idx = seen_slots[slot_key]
            first_s = parsed.sessions[first_idx]
            if first_s.end_time != s.end_time or first_s.location != s.location:
                errors.append(
                    f"Session {idx}: Conflicting duplicate slot key {slot_key} (conflicts with session {first_idx})"
                )
        else:
            seen_slots[slot_key] = idx

    is_valid = len(errors) == 0
    return is_valid, errors


class TimetableProductionWorker:
    """Production worker managing the daily timetable check, parse, validation, and sync."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        max_pages: int = DEFAULT_MAX_PAGES,
        target_levels: Tuple[int, ...] = (1, 2, 3, 4),
        mongo_repo: Optional[MongoTimetableRepository] = None,
        fetcher: Optional[TimetableDownloader] = None,
        scraper: Optional[TimetableScraper] = None,
        dry_run: bool = False,
        force: bool = False,
    ):
        self.base_url = base_url
        self.max_pages = max_pages
        self.target_levels = target_levels
        self.mongo_repo = mongo_repo
        self.fetcher = fetcher or TimetableDownloader()
        self.scraper = scraper or TimetableScraper(base_url=self.base_url, max_pages=self.max_pages)
        self.dry_run = dry_run
        self.force = force

    def discover_and_select_candidates(
        self,
    ) -> Tuple[Dict[int, TimetableCandidate], Dict[int, str], Optional[Tuple[int, int, str, str]]]:
        """Scrape timetable listing, inspect candidate PDFs, and select best candidate per level."""
        logger.info("Discovering notices from %s (max_pages=%d)...", self.base_url, self.max_pages)
        notices = self.scraper.discover_notices()
        if not notices:
            logger.error("No timetable notices could be discovered.")
            return {}, {lvl: "No notices discovered" for lvl in self.target_levels}, None

        logger.info("Discovered %d notices. Inspecting PDF candidates...", len(notices))
        candidates: List[TimetableCandidate] = []

        for notice in notices:
            logger.debug("Evaluating notice: '%s' (%s)", notice.title, notice.publication_date)
            for link_info in notice.pdf_links:
                pdf_bytes = self.fetcher.fetch_pdf_data(link_info.url)
                if not pdf_bytes:
                    logger.warning("Could not download candidate PDF from %s", link_info.url)
                    continue

                is_valid, meta, err = inspect_pdf_bytes(
                    pdf_bytes=pdf_bytes,
                    notice_title=notice.title,
                    fallback_hint=link_info.text,
                )
                if not is_valid or not meta:
                    logger.debug("Skipping invalid candidate PDF %s: %s", link_info.url, err)
                    continue

                candidate = TimetableCandidate(
                    level=meta["level"],
                    academic_year=meta["academic_year"],
                    academic_year_start=meta["academic_year_start"],
                    semester=meta["semester"],
                    semester_num=meta["semester_num"],
                    revision=meta["revision"],
                    revision_rank=meta["revision_rank"],
                    pdf_url=link_info.url,
                    notice_url=notice.url,
                    notice_title=notice.title,
                    publication_date=notice.publication_date,
                    publication_datetime=notice.publication_datetime,
                    pdf_bytes=pdf_bytes,
                    is_valid=True,
                )
                candidates.append(candidate)

        term_info = TimetableSelector.determine_target_academic_term(candidates)
        selected, unselected_reasons = TimetableSelector.select_best_candidates(
            candidates, target_levels=self.target_levels
        )
        return selected, unselected_reasons, term_info

    def run(self) -> int:
        """Execute the production worker lifecycle.

        Returns:
            0 on success (or no changes detected), nonzero exit code on failure.
        """
        start_time = datetime.now(timezone.utc)
        logger.info(
            "Starting Timetable Production Worker (dry_run=%s, force=%s, target_levels=%s)",
            self.dry_run,
            self.force,
            self.target_levels,
        )

        # 1. Candidate discovery & selection
        selected, unselected_reasons, term_info = self.discover_and_select_candidates()
        if not selected:
            logger.error("No valid timetable candidates selected for any target level.")
            self._print_summary(
                term_info=None,
                selected={},
                unchanged=[],
                synchronized={},
                failed={lvl: unselected_reasons.get(lvl, "No candidate found") for lvl in self.target_levels},
                cleanup_success=True,
            )
            return 1

        term_str = f"{term_info[2]} {term_info[3]}" if term_info else "Unknown"
        logger.info("Identified target academic term: %s", term_str)

        # 2. Initialize MongoDB repository
        repo = self.mongo_repo
        managed_locally = False
        if repo is None:
            try:
                repo = MongoTimetableRepository()
                managed_locally = True
                repo.ensure_indexes()
            except Exception as exc:
                logger.error("Failed to connect to MongoDB Atlas: %s", type(exc).__name__)
                print(f"\n[ERROR] Database connection failed: {type(exc).__name__}")
                return 2

        try:
            # 3. Change detection against MongoDB Atlas metadata
            unchanged_levels: List[int] = []
            changed_candidates: Dict[int, TimetableCandidate] = {}
            unselected_levels: Dict[int, str] = {}

            for lvl in self.target_levels:
                if lvl not in selected:
                    reason = unselected_reasons.get(lvl, "No candidate discovered for target term")
                    unselected_levels[lvl] = reason
                    logger.warning("Level %d: %s", lvl, reason)
                    continue

                candidate = selected[lvl]
                candidate_hash = compute_sha256(candidate.pdf_bytes) if candidate.pdf_bytes else ""

                try:
                    existing = repo.collection.find_one({
                        "level": lvl,
                        "academicYear": candidate.academic_year,
                        "semester": candidate.semester,
                    })
                except Exception as exc:
                    logger.error("Database query failed while checking Level %d: %s", lvl, type(exc).__name__)
                    return 2

                if existing and existing.get("sha256") == candidate_hash and not self.force:
                    logger.info(
                        "Level %d (%s %s) unchanged. Stored SHA-256 match (%s...). Skipping writes.",
                        lvl,
                        candidate.academic_year,
                        candidate.semester,
                        candidate_hash[:8],
                    )
                    unchanged_levels.append(lvl)
                else:
                    change_type = "New" if not existing else "Revised"
                    logger.info(
                        "Level %d (%s %s) change detected (%s). Stored hash: %s -> New hash: %s",
                        lvl,
                        candidate.academic_year,
                        candidate.semester,
                        change_type,
                        existing.get("sha256", "None")[:8] if existing else "None",
                        candidate_hash[:8],
                    )
                    changed_candidates[lvl] = candidate

            # 4. If no changes detected, exit cleanly
            if not changed_candidates:
                logger.info("All target levels are up-to-date. No changes detected.")
                self._print_summary(
                    term_info=term_info,
                    selected=selected,
                    unchanged=unchanged_levels,
                    synchronized={},
                    failed=unselected_levels,
                    cleanup_success=True,
                )
                return 0

            # If dry-run mode, report what would be updated without writing
            if self.dry_run:
                logger.info("[DRY RUN] Preview complete. Changes detected for Levels %s. No database writes made.", list(changed_candidates.keys()))
                self._print_summary(
                    term_info=term_info,
                    selected=selected,
                    unchanged=unchanged_levels,
                    synchronized={lvl: {"dry_run": True, "total_sessions": 0, "needs_review": 0} for lvl in changed_candidates},
                    failed=unselected_levels,
                    cleanup_success=True,
                )
                return 0

            # 5. Process changed levels inside an isolated temporary directory
            synchronized: Dict[int, Dict[str, Any]] = {}
            failed: Dict[int, str] = dict(unselected_levels)
            cleanup_success = False

            with tempfile.TemporaryDirectory(prefix="fas_worker_") as temp_dir_str:
                temp_dir = Path(temp_dir_str)
                logger.info("Created temporary workspace at %s", temp_dir)

                for lvl, candidate in changed_candidates.items():
                    logger.info("Processing Level %d timetable PDF temporarily...", lvl)
                    try:
                        # Ensure PDF bytes are available
                        pdf_data = candidate.pdf_bytes
                        if not pdf_data:
                            pdf_data = self.fetcher.fetch_pdf_data(candidate.pdf_url)
                        if not pdf_data:
                            err_msg = f"Failed to download PDF bytes from {candidate.pdf_url}"
                            logger.error("Level %d: %s", lvl, err_msg)
                            failed[lvl] = err_msg
                            continue

                        # Save PDF to temporary workspace
                        temp_pdf = temp_dir / f"level-{lvl}_{candidate.publication_date}.pdf"
                        temp_pdf.write_bytes(pdf_data)

                        # Parse PDF using coordinate-aware parser
                        parser = TimetablePDFParser()
                        parsed = parser.parse_pdf(temp_pdf)

                        # Deduplicate exact duplicate sessions if present
                        deduped_sessions, dedup_count = deduplicate_identical_sessions(parsed.sessions)
                        if dedup_count > 0:
                            logger.info("Level %d: Deduplicated %d exact identical session entries.", lvl, dedup_count)
                            parsed.sessions = deduped_sessions
                            parsed.total_sessions = len(deduped_sessions)

                        # Pre-synchronization validation
                        is_valid, validation_errors = validate_parsed_timetable(parsed)
                        if not is_valid:
                            err_msg = f"Validation failed: {'; '.join(validation_errors)}"
                            logger.error("Level %d: %s. Database remains untouched.", lvl, err_msg)
                            failed[lvl] = err_msg
                            continue

                        # Synchronization: Atomic metadata and session update (with replica set transaction support)
                        now_iso = datetime.now(timezone.utc).astimezone().isoformat()
                        entry = ManifestEntry(
                            level=candidate.level,
                            source_pdf_url=candidate.pdf_url,
                            notice_url=candidate.notice_url,
                            notice_title=candidate.notice_title,
                            publication_date=candidate.publication_date,
                            academic_year=candidate.academic_year,
                            semester=candidate.semester,
                            revision=candidate.revision,
                            download_timestamp=now_iso,
                            local_path=None,
                            file_size=len(pdf_data),
                            sha256=parsed.source_sha256,
                        )

                        if hasattr(repo, "sync_level_atomic"):
                            sync_res = repo.sync_level_atomic(entry, parsed)
                            s_counts = sync_res.get("session_counts", {})
                            meta_action = sync_res.get("metadata_action")
                        else:
                            sess_res = repo.sync_parsed_timetable_sessions(parsed)
                            s_counts = sess_res.get("counts", {})
                            meta_res = repo.sync_timetable_entry(entry)
                            meta_action = meta_res.get("action")

                        synchronized[lvl] = {
                            "source_pdf": candidate.pdf_url.split("/")[-1],
                            "revision": candidate.revision,
                            "sha256": parsed.source_sha256,
                            "total_sessions": parsed.total_sessions,
                            "valid_sessions": parsed.total_sessions - parsed.records_needing_review,
                            "needs_review": parsed.records_needing_review,
                            "metadata_action": meta_action,
                            "session_counts": s_counts,
                        }
                        logger.info(
                            "Level %d synchronized successfully: %d sessions (%d needs review).",
                            lvl,
                            parsed.total_sessions,
                            parsed.records_needing_review,
                        )

                    except Exception as exc:
                        err_msg = f"Processing or sync error: {type(exc).__name__}"
                        logger.error("Level %d failed: %s", lvl, err_msg)
                        failed[lvl] = err_msg

                # Context manager exit removes temp_dir
                cleanup_success = True

            logger.info("Temporary workspace cleaned up. All temporary PDFs removed from disk.")

            # 6. Print final summary
            self._print_summary(
                term_info=term_info,
                selected=selected,
                unchanged=unchanged_levels,
                synchronized=synchronized,
                failed=failed,
                cleanup_success=cleanup_success,
            )

            # Return nonzero exit code if any level failed
            if failed:
                logger.error("Worker completed with failures for levels: %s", list(failed.keys()))
                return 1

            logger.info("Worker completed successfully. All target levels synchronized.")
            return 0

        finally:
            if managed_locally and repo:
                repo.close()

    def _print_summary(
        self,
        term_info: Optional[Tuple[int, int, str, str]],
        selected: Dict[int, TimetableCandidate],
        unchanged: List[int],
        synchronized: Dict[int, Dict[str, Any]],
        failed: Dict[int, str],
        cleanup_success: bool,
    ):
        """Print a structured, non-sensitive summary table for logging and GitHub Actions."""
        term_str = f"{term_info[2]} {term_info[3]}" if term_info else "N/A"

        print("\n" + "=" * 80)
        print("FAS WUSL TIMETABLE PRODUCTION WORKER SUMMARY")
        print("=" * 80)
        print(f"Target Academic Term : {term_str}")
        print(f"Target Levels Checked: {list(self.target_levels)}")
        print(f"Unchanged Levels     : {sorted(unchanged) if unchanged else 'None'}")
        print(f"Synchronized Levels  : {sorted(list(synchronized.keys())) if synchronized else 'None'}")
        print(f"Failed / Missing     : {sorted(list(failed.keys())) if failed else 'None'}")
        print(f"Temporary PDF Cleanup: {'SUCCESS (No PDFs retained)' if cleanup_success else 'FAILED'}")
        print("-" * 80)

        if synchronized:
            print("SYNCHRONIZED TIMETABLES:")
            for lvl in sorted(synchronized.keys()):
                info = synchronized[lvl]
                if info.get("dry_run"):
                    print(f"  Level {lvl}: [DRY RUN] Change detected; writes skipped.")
                else:
                    print(f"  Level {lvl}:")
                    print(f"    Revision       : {info.get('revision')}")
                    print(f"    Source SHA-256 : {info.get('sha256', '')[:16]}...")
                    print(f"    Total Sessions : {info.get('total_sessions')}")
                    print(f"    Valid Sessions : {info.get('valid_sessions')}")
                    print(f"    Needs Review   : {info.get('needs_review')}")
                    counts = info.get("session_counts", {})
                    print(
                        f"    Sync Breakdown : {counts.get('upserted', 0)} upserted, "
                        f"{counts.get('updated', 0)} updated, "
                        f"{counts.get('stale_deleted', 0)} stale deleted."
                    )
            print("-" * 80)

        if failed:
            print("FAILURES AND WARNINGS:")
            for lvl in sorted(failed.keys()):
                print(f"  Level {lvl}: {failed[lvl]}")
            print("-" * 80)

        print("=" * 80 + "\n")


def main():
    """Command-line entry point for production timetable worker."""
    parser = argparse.ArgumentParser(
        description="FAS WUSL Timetable Production Worker: Automated discovery, validation, and MongoDB Atlas sync."
    )
    parser.add_argument(
        "--url",
        type=str,
        default=DEFAULT_BASE_URL,
        help="Base timetable listing page URL",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help="Maximum pagination pages to crawl (default: 5)",
    )
    parser.add_argument(
        "--levels",
        type=int,
        nargs="+",
        default=[1, 2, 3, 4],
        help="Target academic levels (default: 1 2 3 4)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect notices and check for changes without writing to database",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-parsing and re-synchronizing even if SHA-256 hash matches",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose debug logging",
    )

    args = parser.parse_args()
    setup_worker_logging(args.verbose)

    worker = TimetableProductionWorker(
        base_url=args.url,
        max_pages=args.max_pages,
        target_levels=tuple(args.levels),
        dry_run=args.dry_run,
        force=args.force,
    )
    exit_code = worker.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
