"""Production worker for FAS WUSL Academic Calendar synchronization.

Performs automated discovery, SHA-256 change detection, temporary PDF inspection,
rigorous pre-sync validation, deterministic current calendar selection,
MongoDB Atlas synchronization, and guaranteed temporary artifact cleanup.
"""

import argparse
import hashlib
import logging
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set

from .config import (
    DEFAULT_CALENDAR_BASE_URL,
    DEFAULT_MAX_PAGES,
    DEFAULT_MONGODB_DATABASE,
)
from .calendar_models import (
    AcademicCalendarRecord,
    DiscoveredCalendarLink,
    CalendarStatus,
    CalendarValidationStatus,
)
from .calendar_scraper import AcademicCalendarScraper
from .calendar_parser import AcademicCalendarParser
from .calendar_selector import CalendarSelector
from .calendar_repository import MongoCalendarRepository
from .mongodb_repository import MongoTimetableRepository, MongoRepositoryError
from .downloader import TimetableDownloader

logger = logging.getLogger("fas_calendar_worker")


def setup_worker_logging(verbose: bool = False):
    """Setup console logging with standard format."""
    level = logging.DEBUG if verbose else logging.INFO
    format_str = "%(asctime)s [%(levelname)s] %(message)s"
    logging.basicConfig(level=level, format=format_str, datefmt="%Y-%m-%d %H:%M:%S")


class CalendarProductionWorker:
    """Production worker managing the scheduled academic calendar check, parse, validation, and sync."""

    def __init__(
        self,
        base_url: str = DEFAULT_CALENDAR_BASE_URL,
        max_pages: int = DEFAULT_MAX_PAGES,
        mongo_repo: Optional[MongoCalendarRepository] = None,
        fetcher: Optional[TimetableDownloader] = None,
        scraper: Optional[AcademicCalendarScraper] = None,
        parser: Optional[AcademicCalendarParser] = None,
        dry_run: bool = False,
        force: bool = False,
    ):
        self.base_url = base_url
        self.max_pages = max_pages
        self.mongo_repo = mongo_repo
        self.fetcher = fetcher or TimetableDownloader()
        self.scraper = scraper or AcademicCalendarScraper(base_url=self.base_url, max_pages=self.max_pages)
        self.parser = parser or AcademicCalendarParser()
        self.dry_run = dry_run
        self.force = force

    def run(self) -> int:
        """Execute the academic calendar synchronization lifecycle.

        Returns:
            0 on success (including no-change detected), nonzero on failure.
        """
        start_time = datetime.now(timezone.utc)
        logger.info(
            "Starting Academic Calendar Production Worker (dry_run=%s, force=%s)",
            self.dry_run,
            self.force,
        )

        # 1. Source Discovery
        logger.info("Discovering calendar notices from %s...", self.base_url)
        discovered_links = self.scraper.discover_calendar_links()
        now_iso = datetime.now(timezone.utc).astimezone().isoformat()

        if not discovered_links:
            err_msg = f"Failed to discover any academic calendar documents on {self.base_url}"
            logger.error(err_msg)
            # Try recording failure in status repository if possible
            if self.mongo_repo:
                try:
                    self.mongo_repo.update_sync_status({
                        "lastCheckedAt": now_iso,
                        "sourcePageUrl": self.base_url,
                        "discoverySuccess": False,
                        "lastRunFailed": True,
                        "lastError": err_msg,
                    })
                except Exception:
                    pass
            self._print_summary(
                discovered=[],
                unchanged=[],
                synchronized=[],
                failed=[err_msg],
                current_record=None,
                is_confirmed=False,
                selection_reason=err_msg,
            )
            return 1

        logger.info("Discovered %d candidate academic calendar PDF links.", len(discovered_links))

        # 2. Initialize Database Repository if not supplied
        repo = self.mongo_repo
        managed_locally = False
        if repo is None:
            try:
                repo = MongoCalendarRepository()
                managed_locally = True
                repo.ensure_indexes()
            except Exception as exc:
                logger.error("Failed to connect to MongoDB Atlas: %s", type(exc).__name__)
                print(f"\n[ERROR] Database connection failed: {type(exc).__name__}")
                return 2

        try:
            # 3. Retrieve existing records from MongoDB for change detection
            existing_records = {doc["calendarId"]: doc for doc in repo.get_calendars()}
            existing_by_url = {doc["sourceUrl"]: doc for doc in existing_records.values()}
            existing_hashes = {doc["sha256"]: doc for doc in existing_records.values()}

            unchanged_docs: List[str] = []
            parsed_records: List[AcademicCalendarRecord] = []
            failed_docs: List[str] = []
            synchronized_docs: List[str] = []

            # 4. Download and process candidates inside isolated temporary directory
            with tempfile.TemporaryDirectory(prefix="fas_cal_worker_") as temp_dir_str:
                temp_dir = Path(temp_dir_str)
                logger.info("Created temporary workspace at %s", temp_dir)

                for link in discovered_links:
                    logger.debug("Evaluating calendar link: %s (%s)", link.noticeTitle, link.pdfUrl)
                    pdf_data = self.fetcher.fetch_pdf_data(link.pdfUrl)
                    if not pdf_data:
                        err = f"Failed to download PDF from {link.pdfUrl}"
                        logger.warning(err)
                        failed_docs.append(err)
                        continue

                    pdf_hash = hashlib.sha256(pdf_data).hexdigest()

                    # Change detection: If SHA-256 matches existing validated record and not forced
                    if not self.force and pdf_hash in existing_hashes:
                        existing_doc = existing_hashes[pdf_hash]
                        logger.info(
                            "Document unchanged for '%s' (SHA-256 match: %s...). Skipping full parse.",
                            existing_doc.get("documentTitle", link.noticeTitle),
                            pdf_hash[:8],
                        )
                        unchanged_docs.append(f"{existing_doc.get('documentTitle')} ({existing_doc.get('academicYear')})")
                        # Keep existing record for selection
                        try:
                            record = AcademicCalendarRecord(**existing_doc)
                            parsed_records.append(record)
                        except Exception as e:
                            logger.debug("Could not deserialize existing doc, will reparse: %s", e)
                        else:
                            continue

                    # Document is new or changed: Save temporarily and parse
                    temp_pdf_path = temp_dir / f"candidate_{pdf_hash[:8]}.pdf"
                    temp_pdf_path.write_bytes(pdf_data)

                    is_valid, record, warnings = self.parser.parse_pdf(
                        pdf_input=temp_pdf_path,
                        source_url=link.pdfUrl,
                        notice_url=link.noticeUrl,
                        notice_title=link.noticeTitle,
                        publication_date=link.publicationDate,
                    )

                    if not is_valid or not record:
                        err = f"Validation failed for {link.pdfUrl}: {'; '.join(warnings)}"
                        logger.error(err)
                        failed_docs.append(err)
                        continue

                    parsed_records.append(record)

            # 5. Deterministic Current Calendar Selection
            latest_discovered_link = discovered_links[0] if discovered_links else None
            latest_discovered_failed = any(
                latest_discovered_link and (latest_discovered_link.pdfUrl in f or latest_discovered_link.noticeTitle in f)
                for f in failed_docs
            )

            if latest_discovered_failed:
                err_msg = (
                    f"Latest discovered academic calendar notice '{latest_discovered_link.noticeTitle}' "
                    f"failed validation or download ({latest_discovered_link.pdfUrl}). "
                    f"Preserving existing database data."
                )
                logger.error(err_msg)
                if not self.dry_run:
                    repo.update_sync_status({
                        "lastCheckedAt": now_iso,
                        "sourcePageUrl": self.base_url,
                        "discoverySuccess": True,
                        "newerDocumentDiscovered": True,
                        "documentAwaitingValidation": True,
                        "lastRunFailed": True,
                        "lastError": err_msg,
                        "discoveredDocumentsCount": len(discovered_links),
                        "unchangedCount": len(unchanged_docs),
                        "synchronizedCount": len(synchronized_docs),
                        "failedCount": len(failed_docs),
                    })
                self._print_summary(
                    discovered=[l.pdfUrl for l in discovered_links],
                    unchanged=unchanged_docs,
                    synchronized=synchronized_docs,
                    failed=failed_docs,
                    current_record=None,
                    is_confirmed=False,
                    selection_reason=err_msg,
                )
                return 1

            selected_record, is_confirmed, selection_reason = CalendarSelector.select_current_calendar(parsed_records)

            if selected_record:
                logger.info(
                    "Selected active calendar: %s %s (Confirmed: %s). Reason: %s",
                    selected_record.academicYear,
                    selected_record.documentTitle,
                    is_confirmed,
                    selection_reason,
                )

            # 6. Database Upserts
            if not self.dry_run:
                for rec in parsed_records:
                    is_curr = selected_record is not None and rec.calendarId == selected_record.calendarId
                    res = repo.upsert_calendar(
                        record=rec,
                        is_current=is_curr,
                        is_confirmed=is_confirmed if is_curr else False,
                        selection_reason=selection_reason if is_curr else "",
                    )
                    action = res.get("action")
                    if action in ("upserted", "updated"):
                        synchronized_docs.append(f"{rec.documentTitle} ({rec.academicYear}) - {action}")

                # Update global sync status
                repo.update_sync_status({
                    "lastCheckedAt": now_iso,
                    "lastSuccessfulSyncAt": now_iso,
                    "sourcePageUrl": self.base_url,
                    "discoverySuccess": True,
                    "newerDocumentDiscovered": len(synchronized_docs) > 0,
                    "documentAwaitingValidation": len(failed_docs) > 0,
                    "currentCalendarConfirmed": is_confirmed,
                    "currentCalendarId": selected_record.calendarId if selected_record else None,
                    "currentAcademicYear": selected_record.academicYear if selected_record else None,
                    "lastRunFailed": False,
                    "discoveredDocumentsCount": len(discovered_links),
                    "unchangedCount": len(unchanged_docs),
                    "synchronizedCount": len(synchronized_docs),
                    "failedCount": len(failed_docs),
                    "lastError": None if not failed_docs else failed_docs[0],
                })
            else:
                logger.info("[DRY RUN] Preview complete. Database writes skipped.")

            self._print_summary(
                discovered=[l.pdfUrl for l in discovered_links],
                unchanged=unchanged_docs,
                synchronized=synchronized_docs,
                failed=failed_docs,
                current_record=selected_record,
                is_confirmed=is_confirmed,
                selection_reason=selection_reason,
            )

            # Return success if at least some valid records are processed and no fatal crash
            return 0 if not (len(failed_docs) > 0 and len(parsed_records) == 0) else 1

        except Exception as exc:
            logger.exception("Unexpected error during calendar worker run: %s", exc)
            return 2
        finally:
            if managed_locally and repo:
                try:
                    repo.client.close()
                except Exception:
                    pass

    def _print_summary(
        self,
        discovered: List[str],
        unchanged: List[str],
        synchronized: List[str],
        failed: List[str],
        current_record: Optional[AcademicCalendarRecord],
        is_confirmed: bool,
        selection_reason: str,
    ):
        """Print structured ASCII summary report to standard output."""
        print("\n" + "=" * 80)
        print("FAS WUSL ACADEMIC CALENDAR SYNCHRONIZATION SUMMARY")
        print("=" * 80)
        print(f"Discovered Sources   : {len(discovered)}")
        print(f"Unchanged Documents  : {len(unchanged)}")
        print(f"Synchronized Updates : {len(synchronized)}")
        print(f"Validation Failures  : {len(failed)}")
        if current_record:
            print("-" * 80)
            print("CURRENT ACTIVE CALENDAR:")
            print(f"  Academic Year      : {current_record.academicYear}")
            print(f"  Document Title     : {current_record.documentTitle}")
            print(f"  Document Status    : {current_record.documentStatus.value}")
            print(f"  Levels Covered     : {current_record.levels}")
            print(f"  Semesters Covered  : {current_record.semesters}")
            print(f"  Confirmed Status   : {'CONFIRMED' if is_confirmed else 'UNCONFIRMED'}")
            print(f"  Selection Reason   : {selection_reason}")
            print(f"  Total Activities   : {current_record.activitiesCount}")
            print(f"  Source PDF URL     : {current_record.sourceUrl}")
        else:
            print("-" * 80)
            print("CURRENT ACTIVE CALENDAR: None available")

        if failed:
            print("-" * 80)
            print("FAILURES AND WARNINGS:")
            for f in failed:
                print(f"  - {f}")

        print("=" * 80 + "\n")


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments for the academic calendar worker."""
    parser = argparse.ArgumentParser(
        description="FAS WUSL Academic Calendar Daily Production Worker"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying MongoDB Atlas",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-parsing and writing even if SHA-256 hash matches",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable detailed debug logging",
    )
    return parser.parse_args(args)


def main():
    """Main CLI entry point for Academic Calendar production worker."""
    parsed_args = parse_args()
    setup_worker_logging(verbose=parsed_args.verbose)

    worker = CalendarProductionWorker(
        dry_run=parsed_args.dry_run,
        force=parsed_args.force,
    )
    exit_code = worker.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
