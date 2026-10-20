"""Unit tests for FAS WUSL Academic Calendar production worker."""

import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile

from src.calendar_worker import CalendarProductionWorker
from src.calendar_models import (
    DiscoveredCalendarLink,
    AcademicCalendarRecord,
    CalendarStatus,
    CalendarValidationStatus,
)


class TestCalendarProductionWorker(unittest.TestCase):

    def setUp(self):
        self.mock_repo = MagicMock()
        self.mock_fetcher = MagicMock()
        self.mock_scraper = MagicMock()
        self.mock_parser = MagicMock()

        self.worker = CalendarProductionWorker(
            mongo_repo=self.mock_repo,
            fetcher=self.mock_fetcher,
            scraper=self.mock_scraper,
            parser=self.mock_parser,
            dry_run=False,
            force=False,
        )

    def _mock_record(self, cal_id="cal_2024_2025", sha256="hash123") -> AcademicCalendarRecord:
        return AcademicCalendarRecord(
            calendarId=cal_id,
            academicYear="2024/2025",
            academicYearStart=2024,
            academicYearEnd=2025,
            documentTitle="CALENDAR OF DATES",
            documentStatus=CalendarStatus.APPROVED,
            revision="Original",
            revisionRank=2,
            levels=[1, 2, 3, 4],
            semesters=["Semester I"],
            sourceUrl="https://fas.wyb.ac.lk/uploads/COD-2024-2025.pdf",
            sha256=sha256,
            firstSeenAt="2026-10-20T12:00:00+05:30",
            lastSeenAt="2026-10-20T12:00:00+05:30",
            lastValidatedAt="2026-10-20T12:00:00+05:30",
            validationStatus=CalendarValidationStatus.VALID,
            activitiesCount=1,
            activities=[],
            updatedAt="2026-10-20T12:00:00+05:30",
        )

    def test_run_discovery_failure_returns_1(self):
        self.mock_scraper.discover_calendar_links.return_value = []
        code = self.worker.run()
        self.assertEqual(code, 1)
        self.mock_repo.update_sync_status.assert_called_once()
        status_arg = self.mock_repo.update_sync_status.call_args[0][0]
        self.assertFalse(status_arg["discoverySuccess"])
        self.assertTrue(status_arg["lastRunFailed"])

    def test_run_success_with_new_document(self):
        discovered = [
            DiscoveredCalendarLink(
                noticeTitle="Calendar 2024/2025",
                noticeUrl="https://fas.wyb.ac.lk/notice/",
                pdfUrl="https://fas.wyb.ac.lk/uploads/COD-2024-2025.pdf",
                publicationDate="2026-07-17",
            )
        ]
        self.mock_scraper.discover_calendar_links.return_value = discovered
        self.mock_repo.get_calendars.return_value = []
        self.mock_fetcher.fetch_pdf_data.return_value = b"%PDF-1.4 sample content"

        record = self._mock_record()
        self.mock_parser.parse_pdf.return_value = (True, record, [])
        self.mock_repo.upsert_calendar.return_value = {"action": "upserted", "calendarId": record.calendarId}

        code = self.worker.run()
        self.assertEqual(code, 0)
        self.mock_repo.upsert_calendar.assert_called_once()
        self.mock_repo.update_sync_status.assert_called_once()
        status_arg = self.mock_repo.update_sync_status.call_args[0][0]
        self.assertTrue(status_arg["discoverySuccess"])
        self.assertEqual(status_arg["synchronizedCount"], 1)

    def test_run_unchanged_document_skips_parsing(self):
        record = self._mock_record(sha256="a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3")
        discovered = [
            DiscoveredCalendarLink(
                noticeTitle="Calendar 2024/2025",
                noticeUrl="https://fas.wyb.ac.lk/notice/",
                pdfUrl="https://fas.wyb.ac.lk/uploads/COD-2024-2025.pdf",
                publicationDate="2026-07-17",
            )
        ]
        self.mock_scraper.discover_calendar_links.return_value = discovered
        self.mock_repo.get_calendars.return_value = [record.model_dump()]
        self.mock_fetcher.fetch_pdf_data.return_value = b"123"  # matches hash above

        self.mock_repo.upsert_calendar.return_value = {"action": "skipped", "calendarId": record.calendarId}

        code = self.worker.run()
        self.assertEqual(code, 0)
        # Parse should not be called since document is unchanged
        self.mock_parser.parse_pdf.assert_not_called()

    def test_run_dry_run_skips_database_writes(self):
        self.worker.dry_run = True
        discovered = [
            DiscoveredCalendarLink(
                noticeTitle="Calendar 2024/2025",
                noticeUrl="https://fas.wyb.ac.lk/notice/",
                pdfUrl="https://fas.wyb.ac.lk/uploads/COD-2024-2025.pdf",
                publicationDate="2026-07-17",
            )
        ]
        self.mock_scraper.discover_calendar_links.return_value = discovered
        self.mock_repo.get_calendars.return_value = []
        self.mock_fetcher.fetch_pdf_data.return_value = b"%PDF-1.4 sample content"

        record = self._mock_record()
        self.mock_parser.parse_pdf.return_value = (True, record, [])

        code = self.worker.run()
        self.assertEqual(code, 0)
        self.mock_repo.upsert_calendar.assert_not_called()
