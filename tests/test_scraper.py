"""Unit tests for scraper and date parser."""

import unittest
from datetime import datetime
from src.scraper import parse_date_string, TimetableScraper
from unittest.mock import MagicMock, patch


SAMPLE_LISTING_HTML = """
<html>
<body>
<div class="elementor-widget-posts">
  <article class="elementor-post elementor-grid-item post-1 type-post status-publish">
    <div class="elementor-post__text">
      <h3 class="elementor-post__title">
        <a href="https://fas.wyb.ac.lk/revised-level-1/">Revised – Level 1</a>
      </h3>
      <span class="elementor-post-date">October 5, 2026</span>
    </div>
  </article>
  <article class="elementor-post elementor-grid-item post-2 type-post status-publish">
    <div class="elementor-post__text">
      <h3 class="elementor-post__title">
        <a href="https://fas.wyb.ac.lk/all-levels/">Academic Time Table – Level 1,2,3 & 4</a>
      </h3>
      <span class="elementor-post-date">September 10, 2026</span>
    </div>
  </article>
  <div class="e-load-more-anchor" data-max-page="2" data-next-page="https://fas.wyb.ac.lk/timetables/2/"></div>
</div>
</body>
</html>
"""

SAMPLE_NOTICE_HTML = """
<html>
<body>
  <div class="entry-content">
    <a href="https://fas.wyb.ac.lk/wp-content/uploads/2026/10/Level-1.pdf">Level 01</a>
    <a href="https://fas.wyb.ac.lk/wp-content/uploads/2026/10/Level-2.pdf">Level 02</a>
  </div>
</body>
</html>
"""


class TestScraper(unittest.TestCase):

    def test_parse_date_strings(self):
        self.assertEqual(
            parse_date_string("October 5, 2026"),
            datetime(2026, 10, 5),
        )
        self.assertEqual(
            parse_date_string("July 30, 2026"),
            datetime(2026, 7, 30),
        )
        self.assertEqual(
            parse_date_string("2026-09-10"),
            datetime(2026, 9, 10),
        )
        self.assertIsNone(parse_date_string("Not a valid date"))

    def test_scraper_discover_and_parse(self):
        scraper = TimetableScraper(base_url="https://fas.wyb.ac.lk/timetables/", max_pages=1)
        
        def fake_fetch(url):
            if "timetables" in url:
                return SAMPLE_LISTING_HTML
            return SAMPLE_NOTICE_HTML

        with patch.object(scraper, "fetch_page", side_effect=fake_fetch):
            notices = scraper.discover_notices()
            self.assertEqual(len(notices), 2)
            self.assertEqual(notices[0].title, "Revised – Level 1")
            self.assertEqual(notices[0].publication_date, "2026-10-05")
            self.assertEqual(len(notices[0].pdf_links), 2)
            self.assertEqual(notices[0].pdf_links[0].url, "https://fas.wyb.ac.lk/wp-content/uploads/2026/10/Level-1.pdf")
            self.assertEqual(notices[0].pdf_links[0].text, "Level 01")


if __name__ == "__main__":
    unittest.main()
