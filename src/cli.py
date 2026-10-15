"""Command-line interface and main coordinator for FAS timetable downloader and parser."""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Optional

from .config import (
    DEFAULT_BASE_URL,
    DEFAULT_DOWNLOADS_DIR,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_PARSED_DIR,
    DEFAULT_MAX_PAGES,
)
from .downloader import TimetableDownloader
from .models import TimetableCandidate, ManifestEntry
from .mongodb_repository import MongoTimetableRepository, MongoRepositoryError
from .parser_models import ParsedTimetable
from .pdf_inspector import inspect_pdf_bytes
from .scraper import TimetableScraper
from .selector import TimetableSelector
from .timetable_parser import TimetablePDFParser

logger = logging.getLogger("fas_downloader")


def setup_logging(verbose: bool = False):
    """Setup console logging format and level."""
    level = logging.DEBUG if verbose else logging.INFO
    format_str = "%(asctime)s [%(levelname)s] %(message)s"
    logging.basicConfig(level=level, format=format_str, datefmt="%Y-%m-%d %H:%M:%S")


def run_parse(
    downloads_dir: Path = DEFAULT_DOWNLOADS_DIR,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    parsed_dir: Path = DEFAULT_PARSED_DIR,
) -> int:
    """Parse downloaded timetable PDFs and export structured JSON files."""
    parser = TimetablePDFParser(parsed_output_dir=parsed_dir)
    print("\n" + "=" * 80)
    print("PARSING DOWNLOADED TIMETABLE PDFS")
    print("=" * 80)
    results = parser.parse_all_downloaded(
        downloads_dir=downloads_dir,
        manifest_path=manifest_path,
        output_dir=parsed_dir,
    )
    if not results:
        logger.error("No timetable PDFs found in %s to parse.", downloads_dir)
        print(f"\n[ERROR] No PDFs found in {downloads_dir} to parse.")
        return 1

    print("\n" + "=" * 80)
    print("PARSER EXTRACTION SUMMARY")
    print("=" * 80)
    for lvl in sorted(results.keys()):
        p = results[lvl]
        valid_count = p.total_sessions - p.records_needing_review
        print(f"Level {lvl}:")
        print(f"  Source PDF         : {p.source_pdf}")
        print(f"  Academic Term      : {p.academic_year} {p.semester} ({p.revision})")
        print(f"  Total Sessions     : {p.total_sessions}")
        print(f"  Valid Sessions     : {valid_count}")
        print(f"  Needs Review       : {p.records_needing_review}")
        print(f"  Parser Warnings    : {len(p.warnings)}")
        print(f"  Exported File      : {parsed_dir / f'level-{lvl}.json'}")
        print("-" * 80)

    print(f"\nAll parsed files successfully exported to {parsed_dir}/")
    return 0


def run_sync_parsed_to_mongodb(
    parsed_dir: Path = DEFAULT_PARSED_DIR,
    dry_run: bool = False,
    mongo_repo: Optional[MongoTimetableRepository] = None,
) -> int:
    """Synchronize existing parsed timetable JSON files in parsed_dir to MongoDB Atlas."""
    parsed_dir = Path(parsed_dir)
    json_files = sorted(parsed_dir.glob("level-*.json"))
    if not json_files:
        logger.error("No parsed JSON files found in %s to synchronize.", parsed_dir)
        print(f"\n[ERROR] No parsed JSON files found in {parsed_dir}/ to synchronize.")
        return 1

    parsed_timetables: Dict[int, ParsedTimetable] = {}
    for jf in json_files:
        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
            pt = ParsedTimetable.model_validate(data)
            parsed_timetables[pt.level] = pt
        except Exception as exc:
            logger.error("Failed to parse JSON file %s: %s", jf.name, exc)
            print(f"\n[ERROR] Corrupt or invalid JSON file: {jf.name} ({exc})")
            return 1

    print("\n" + "=" * 80)
    print("SYNCHRONIZING PARSED SESSIONS TO MONGODB ATLAS")
    print("=" * 80)
    for lvl in sorted(parsed_timetables.keys()):
        pt = parsed_timetables[lvl]
        valid_count = pt.total_sessions - pt.records_needing_review
        print(
            f"Level {lvl}: {pt.total_sessions} sessions "
            f"(Valid: {valid_count}, Needs Review: {pt.records_needing_review}) "
            f"from {pt.source_pdf}"
        )

    if dry_run:
        print("\n[DRY RUN] MongoDB synchronization preview complete. No database changes were made.")
        return 0

    repo = mongo_repo
    managed_locally = False
    if repo is None:
        try:
            repo = MongoTimetableRepository()
            managed_locally = True
        except Exception as exc:
            logger.error("Failed to connect to MongoDB: %s", type(exc).__name__)
            print(f"\n[ERROR] MongoDB connection failed: {type(exc).__name__}.")
            return 2

    try:
        sync_result = repo.sync_all_parsed_sessions(parsed_timetables)
        totals = sync_result.get("totals", {})
        print(
            f"\nMongoDB sessions synchronization complete: "
            f"{totals.get('upserted', 0)} upserted, "
            f"{totals.get('updated', 0)} updated, "
            f"{totals.get('skipped', 0)} skipped, "
            f"{totals.get('stale_deleted', 0)} stale deleted."
        )
        return 0
    except Exception as exc:
        logger.error("MongoDB sessions synchronization failed: %s", type(exc).__name__)
        print(f"\n[ERROR] MongoDB sessions synchronization failed: {type(exc).__name__}.")
        return 2
    finally:
        if managed_locally and repo:
            repo.close()


def run(
    base_url: str = DEFAULT_BASE_URL,
    downloads_dir: Path = DEFAULT_DOWNLOADS_DIR,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    parsed_dir: Path = DEFAULT_PARSED_DIR,
    max_pages: int = DEFAULT_MAX_PAGES,
    dry_run: bool = False,
    skip_mongodb: bool = False,
    target_levels: tuple = (1, 2, 3, 4),
    mongo_repo: Optional[MongoTimetableRepository] = None,
) -> int:
    """Execute discovery, inspection, selection, download, parsing, and MongoDB sync."""
    logger.info(
        "Starting FAS WUSL Timetable Downloader (dry_run=%s, skip_mongodb=%s)",
        dry_run,
        skip_mongodb,
    )
    logger.info("Listing URL: %s", base_url)

    scraper = TimetableScraper(base_url=base_url, max_pages=max_pages)
    notices = scraper.discover_notices()

    if not notices:
        logger.error("No timetable notices could be discovered.")
        return 1

    logger.info("Discovered %d notices. Inspecting PDF candidates...", len(notices))

    candidates: List[TimetableCandidate] = []
    ambiguous_or_invalid: List[Dict[str, str]] = []

    # Downloader helper for network fetching if needed
    fetcher = TimetableDownloader()

    for notice in notices:
        logger.info("Evaluating notice: '%s' (%s)", notice.title, notice.publication_date)
        for link_info in notice.pdf_links:
            pdf_bytes = fetcher.fetch_pdf_data(link_info.url)
            if not pdf_bytes:
                ambiguous_or_invalid.append({
                    "url": link_info.url,
                    "notice": notice.title,
                    "reason": "Could not download PDF data",
                })
                continue

            is_valid, meta, err = inspect_pdf_bytes(
                pdf_bytes=pdf_bytes,
                notice_title=notice.title,
                fallback_hint=link_info.text,
            )

            if not is_valid or not meta:
                logger.warning(
                    "Skipping unreadable or ambiguous candidate: %s | Reason: %s",
                    link_info.url,
                    err,
                )
                ambiguous_or_invalid.append({
                    "url": link_info.url,
                    "notice": notice.title,
                    "reason": err or "Unknown validation error",
                })
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
            logger.debug(
                "Parsed candidate: Level %d | %s %s | %s | %s",
                candidate.level,
                candidate.academic_year,
                candidate.semester,
                candidate.revision,
                candidate.pdf_url,
            )

    # Perform candidate selection
    selected, unselected_reasons = TimetableSelector.select_best_candidates(
        candidates, target_levels=target_levels
    )

    # Print summary table
    print("\n" + "=" * 80)
    print("TIMETABLE CANDIDATE SELECTION SUMMARY")
    print("=" * 80)

    for lvl in target_levels:
        if lvl in selected:
            cand = selected[lvl]
            print(f"Level {lvl}:")
            print(f"  Academic Year    : {cand.academic_year}")
            print(f"  Semester         : {cand.semester}")
            print(f"  Revision         : {cand.revision}")
            print(f"  Publication Date : {cand.publication_date}")
            print(f"  Notice Title     : {cand.notice_title}")
            print(f"  Notice URL       : {cand.notice_url}")
            print(f"  Source PDF URL   : {cand.pdf_url}")
        else:
            reason = unselected_reasons.get(lvl, "Unidentified")
            print(f"Level {lvl}: [NOT IDENTIFIED] - {reason}")
        print("-" * 80)

    if ambiguous_or_invalid:
        print("\nAMBIGUOUS OR INVALID CANDIDATES SKIPPED:")
        for item in ambiguous_or_invalid:
            print(f"- {item['url']} (Notice: {item['notice']}) -> {item['reason']}")

    if dry_run:
        print("\n[DRY RUN] No files downloaded to disk. manifest.json was not updated. MongoDB was not modified.")
        return 0

    # Execute downloads and manifest update
    downloader = TimetableDownloader(
        downloads_dir=downloads_dir,
        manifest_path=manifest_path,
    )

    downloaded_entries: Dict[int, ManifestEntry] = {}
    for lvl, candidate in selected.items():
        entry = downloader.download_and_save(candidate)
        if entry:
            downloaded_entries[lvl] = entry

    parsed_timetables: Dict[int, ParsedTimetable] = {}
    if downloaded_entries:
        first_cand = next(iter(selected.values()))
        downloader.update_manifest(
            downloaded_entries,
            target_academic_year=first_cand.academic_year,
            target_semester=first_cand.semester,
        )
        print(f"\nSuccessfully downloaded {len(downloaded_entries)} timetables into {downloads_dir}/")
        print(f"Manifest written to {manifest_path}")

        # Parse downloaded PDFs into data/parsed/
        parser = TimetablePDFParser(parsed_output_dir=parsed_dir)
        parsed_timetables = parser.parse_all_downloaded(
            downloads_dir=downloads_dir,
            manifest_path=manifest_path,
            output_dir=parsed_dir,
        )

    all_downloaded = all(lvl in downloaded_entries for lvl in target_levels)

    # MongoDB Synchronization step
    if skip_mongodb:
        logger.info("Skipping MongoDB synchronization (--skip-mongodb specified).")
        return 0 if all_downloaded else 1

    logger.info("Synchronizing timetable metadata and sessions to MongoDB Atlas...")
    repo = mongo_repo
    managed_locally = False
    if repo is None:
        try:
            repo = MongoTimetableRepository()
            managed_locally = True
        except Exception as exc:
            logger.error("Failed to connect to MongoDB: %s", type(exc).__name__)
            print(f"\n[ERROR] MongoDB connection failed: {type(exc).__name__}.")
            print("Downloaded PDFs and manifest.json remain intact on disk.")
            return 2

    try:
        # 1. Sync metadata to timetables
        sync_result = repo.sync_all(downloaded_entries)
        counts = sync_result.get("counts", {})
        print(
            f"MongoDB metadata synchronization complete: {counts.get('upserted', 0)} upserted, "
            f"{counts.get('updated', 0)} updated, {counts.get('skipped', 0)} skipped."
        )

        # 2. Sync parsed sessions to timetable_sessions
        if parsed_timetables:
            sess_result = repo.sync_all_parsed_sessions(parsed_timetables)
            s_totals = sess_result.get("totals", {})
            print(
                f"MongoDB sessions synchronization complete: {s_totals.get('upserted', 0)} upserted, "
                f"{s_totals.get('updated', 0)} updated, {s_totals.get('skipped', 0)} skipped, "
                f"{s_totals.get('stale_deleted', 0)} stale deleted."
            )
    except Exception as exc:
        logger.error("MongoDB synchronization failed: %s", type(exc).__name__)
        print(f"\n[ERROR] MongoDB synchronization failed: {type(exc).__name__}.")
        print("Downloaded PDFs and manifest.json remain intact on disk.")
        return 2
    finally:
        if managed_locally and repo:
            repo.close()

    return 0 if all_downloaded else 1


def main():
    parser = argparse.ArgumentParser(
        description="FAS WUSL Timetable Downloader: Discover, download, parse, and synchronize academic timetables."
    )
    parser.add_argument(
        "--sync-parsed-to-mongodb",
        action="store_true",
        help="Synchronize existing parsed JSON files from data/parsed/ to MongoDB Atlas.",
    )
    parser.add_argument(
        "--worker",
        action="store_true",
        help="Run the production automation worker (scheduled discovery, change detection, validation, scoped sync, and temporary cleanup)",
    )
    parser.add_argument(
        "--parse-only",
        action="store_true",
        help="Parse existing downloaded PDFs and export JSON without downloading or connecting to MongoDB.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect notices and select candidates without downloading files or modifying manifest/database.",
    )
    parser.add_argument(
        "--skip-mongodb",
        action="store_true",
        help="Perform normal local download and manifest update, but skip MongoDB synchronization.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_DOWNLOADS_DIR,
        help="Directory to save downloaded PDF files (default: downloads)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help="Path for manifest.json (default: metadata/manifest.json)",
    )
    parser.add_argument(
        "--parsed-dir",
        type=Path,
        default=DEFAULT_PARSED_DIR,
        help="Directory to export parsed JSON files (default: data/parsed)",
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
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.sync_parsed_to_mongodb:
        exit_code = run_sync_parsed_to_mongodb(
            parsed_dir=args.parsed_dir,
            dry_run=args.dry_run,
        )
        sys.exit(exit_code)

    if args.worker:
        from .worker import TimetableProductionWorker
        worker = TimetableProductionWorker(
            base_url=args.url,
            max_pages=args.max_pages,
            dry_run=args.dry_run,
        )
        sys.exit(worker.run())

    if args.parse_only:
        exit_code = run_parse(
            downloads_dir=args.output_dir,
            manifest_path=args.manifest,
            parsed_dir=args.parsed_dir,
        )
        sys.exit(exit_code)

    exit_code = run(
        base_url=args.url,
        downloads_dir=args.output_dir,
        manifest_path=args.manifest,
        parsed_dir=args.parsed_dir,
        max_pages=args.max_pages,
        dry_run=args.dry_run,
        skip_mongodb=args.skip_mongodb,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
