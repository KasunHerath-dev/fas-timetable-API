"""PDF file downloader, validator, and manifest management."""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

import pymupdf
import requests

from .config import DEFAULT_DOWNLOADS_DIR, DEFAULT_MANIFEST_PATH, REQUEST_TIMEOUT, DEFAULT_USER_AGENT
from .models import TimetableCandidate, ManifestEntry

logger = logging.getLogger(__name__)


def compute_sha256(data: bytes) -> str:
    """Compute hex SHA-256 digest of bytes."""
    return hashlib.sha256(data).hexdigest()


class TimetableDownloader:
    """Manages downloading selected timetable PDFs and writing manifest.json."""

    def __init__(
        self,
        downloads_dir: Path = DEFAULT_DOWNLOADS_DIR,
        manifest_path: Path = DEFAULT_MANIFEST_PATH,
        session: Optional[requests.Session] = None,
    ):
        self.downloads_dir = Path(downloads_dir)
        self.manifest_path = Path(manifest_path)
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": DEFAULT_USER_AGENT})

    def fetch_pdf_data(self, url: str) -> Optional[bytes]:
        """Fetch PDF bytes from URL with timeout and error handling."""
        try:
            logger.debug("Downloading PDF from %s", url)
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                logger.error("Failed to download PDF from %s: HTTP %d", url, resp.status_code)
                return None
            return resp.content
        except requests.RequestException as exc:
            logger.error("Network error downloading PDF %s: %s", url, exc)
            return None

    def verify_pdf_data(self, data: bytes) -> Tuple[bool, Optional[str]]:
        """Verify that the byte array is a valid readable PDF."""
        if not data:
            return False, "Data is empty"
        try:
            doc = pymupdf.open(stream=data, filetype="pdf")
            if doc.page_count < 1:
                doc.close()
                return False, "PDF has 0 pages"
            # Read first page
            _ = doc[0].get_text()
            doc.close()
            return True, None
        except Exception as exc:
            return False, f"Invalid or corrupt PDF: {exc}"

    def load_existing_manifest(self) -> Dict[str, Any]:
        """Load existing manifest if it exists on disk, else return empty dict."""
        if not self.manifest_path.exists():
            return {}
        try:
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("Could not read existing manifest %s: %s", self.manifest_path, exc)
            return {}

    def download_and_save(
        self,
        candidate: TimetableCandidate,
    ) -> Optional[ManifestEntry]:
        """Download and verify PDF for candidate, saving into downloads/."""
        # Ensure downloads dir exists
        self.downloads_dir.mkdir(parents=True, exist_ok=True)

        data = candidate.pdf_bytes
        if not data:
            data = self.fetch_pdf_data(candidate.pdf_url)

        if not data:
            logger.error("Could not obtain PDF content for Level %d (%s)", candidate.level, candidate.pdf_url)
            return None

        # Verify readable PDF
        is_valid, err = self.verify_pdf_data(data)
        if not is_valid:
            logger.error("PDF verification failed for Level %d: %s", candidate.level, err)
            return None

        # Determine filename: level-{level}_{YYYY-MM-DD}.pdf
        filename = f"level-{candidate.level}_{candidate.publication_date}.pdf"
        target_path = self.downloads_dir / filename

        # Write to file
        try:
            target_path.write_bytes(data)
            logger.info("Saved Level %d timetable to %s", candidate.level, target_path)
        except IOError as exc:
            logger.error("Failed to write PDF to %s: %s", target_path, exc)
            return None

        # Create manifest entry
        file_size = len(data)
        sha256_hash = compute_sha256(data)
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
            local_path=str(target_path),
            file_size=file_size,
            sha256=sha256_hash,
        )
        return entry

    def update_manifest(
        self,
        new_entries: Dict[int, ManifestEntry],
        target_academic_year: str = "",
        target_semester: str = "",
    ) -> bool:
        """Update or create metadata/manifest.json safely."""
        existing = self.load_existing_manifest()
        levels_dict = existing.get("levels", {})

        for lvl, entry in new_entries.items():
            levels_dict[str(lvl)] = entry.to_dict()

        manifest_data = {
            "last_updated": datetime.now(timezone.utc).astimezone().isoformat(),
            "target_academic_year": target_academic_year or existing.get("target_academic_year", ""),
            "target_semester": target_semester or existing.get("target_semester", ""),
            "levels": levels_dict,
        }

        # Atomic write
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.manifest_path.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2, ensure_ascii=False)
            tmp_path.replace(self.manifest_path)
            logger.info("Manifest updated at %s", self.manifest_path)
            return True
        except Exception as exc:
            logger.error("Failed to update manifest at %s: %s", self.manifest_path, exc)
            if tmp_path.exists():
                tmp_path.unlink()
            return False
