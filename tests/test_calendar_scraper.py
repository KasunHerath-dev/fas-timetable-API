"""Unit tests for FAS WUSL Academic Calendar scraper."""

import unittest
from unittest.mock import MagicMock
import requests
from src.calendar_scraper import AcademicCalendarScraper


class TestAcademicCalendarScraper(unittest.TestCase):

    def setUp(self):
        self.mock_session = MagicMock()
        self.mock_session.headers = {}
        self.scraper = AcademicCalendarScraper(
            base_url="https://fas.wyb.ac.lk/timetables/academic-calendar/",
            session=self.mock_session,
        )

    def test_discover_calendar_links_elementor_cards(self):
        listing_html = """
        <html><body>
            <article class="elementor-post elementor-grid-item type-post">
                <h3 class="elementor-post__title">
                    <a href="https://fas.wyb.ac.lk/calendar-of-dates-2024-2025/">Calendar of Dates for Academic Year 2024/2025</a>
                </h3>
                <span class="elementor-post-date">July 17, 2026</span>
            </article>
            <article class="elementor-post elementor-grid-item type-post">
                <h3 class="elementor-post__title">
                    <a href="/draft-calendar-2023-2024/">Draft Calendar of Dates 2023/2024</a>
                </h3>
                <time datetime="2026-02-09">February 9, 2026</time>
            </article>
            <article class="elementor-post elementor-grid-item type-post">
                <h3 class="elementor-post__title">
                    <a href="https://fas.wyb.ac.lk/unrelated-news/">Unrelated News</a>
                </h3>
            </article>
        </body></html>
        """
        notice_html_1 = """
        <html><body>
            <h1>Calendar of Dates for Academic Year 2024/2025</h1>
            <a href="https://fas.wyb.ac.lk/uploads/COD-2024-2025.pdf">Download Notice PDF</a>
        </body></html>
        """
        notice_html_2 = """
        <html><body>
            <h1>Draft Calendar of Dates</h1>
            <a href="/uploads/COD-Draft.pdf">Download PDF</a>
        </body></html>
        """

        def mock_get(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            if "timetables/academic-calendar" in url:
                resp.text = listing_html
            elif "calendar-of-dates-2024-2025" in url:
                resp.text = notice_html_1
            elif "draft-calendar-2023-2024" in url:
                resp.text = notice_html_2
            else:
                resp.text = "<html><body></body></html>"
            return resp

        self.mock_session.get.side_effect = mock_get

        links = self.scraper.discover_calendar_links()
        self.assertEqual(len(links), 2)

        link1 = links[0]
        self.assertEqual(link1.pdfUrl, "https://fas.wyb.ac.lk/uploads/COD-2024-2025.pdf")
        self.assertEqual(link1.publicationDate, "2026-07-17")
        self.assertIn("2024/2025", link1.noticeTitle)

        link2 = links[1]
        self.assertEqual(link2.pdfUrl, "https://fas.wyb.ac.lk/uploads/COD-Draft.pdf")
        self.assertEqual(link2.publicationDate, "2026-02-09")

    def test_direct_pdf_links_on_listing_page_fallback(self):
        listing_html = """
        <html><body>
            <div class="content">
                <p>Welcome to academic calendar page.</p>
                <a href="/wp-content/uploads/COD-Direct.pdf">Calendar of Dates 2024/2025 Direct PDF</a>
            </div>
        </body></html>
        """
        resp = MagicMock()
        resp.status_code = 200
        resp.text = listing_html
        self.mock_session.get.return_value = resp

        links = self.scraper.discover_calendar_links()
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].pdfUrl, "https://fas.wyb.ac.lk/wp-content/uploads/COD-Direct.pdf")

    def test_network_failure_handling(self):
        self.mock_session.get.side_effect = requests.RequestException("Connection refused")
        links = self.scraper.discover_calendar_links()
        self.assertEqual(links, [])

    def test_http_404_error_handling(self):
        resp = MagicMock()
        resp.status_code = 404
        self.mock_session.get.return_value = resp

        links = self.scraper.discover_calendar_links()
        self.assertEqual(links, [])
