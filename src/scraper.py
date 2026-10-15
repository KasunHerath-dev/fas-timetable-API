"""Web scraper for FAS WUSL timetable notices and PDF links."""

import logging
from datetime import datetime
from typing import List, Optional, Set
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .config import DEFAULT_BASE_URL, DEFAULT_USER_AGENT, DEFAULT_MAX_PAGES, REQUEST_TIMEOUT
from .models import Notice, PDFLinkInfo

logger = logging.getLogger(__name__)


def parse_date_string(date_str: str) -> Optional[datetime]:
    """Parse various date string formats into a datetime object."""
    if not date_str:
        return None

    cleaned = date_str.strip()
    # Common formats
    formats = [
        "%B %d, %Y",       # October 5, 2026
        "%b %d, %Y",        # Oct 5, 2026
        "%d %B %Y",        # 5 October 2026
        "%d %b %Y",         # 5 Oct 2026
        "%Y-%m-%d",        # 2026-10-05
        "%d/%m/%Y",        # 05/10/2026
        "%m/%d/%Y",        # 10/05/2026
        "%d-%m-%Y",        # 05-10-2026
    ]

    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue

    logger.warning("Could not parse date string: %r", date_str)
    return None


class TimetableScraper:
    """Scrapes timetable notice listings and individual notice pages."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        user_agent: str = DEFAULT_USER_AGENT,
        max_pages: int = DEFAULT_MAX_PAGES,
        session: Optional[requests.Session] = None,
    ):
        self.base_url = base_url
        self.max_pages = max_pages
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch HTML content from a URL with safe error handling."""
        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                logger.warning("GET %s returned HTTP status %d", url, resp.status_code)
                return None
            return resp.text
        except requests.RequestException as exc:
            logger.error("Network error fetching %s: %s", url, exc)
            return None

    def discover_notices(self) -> List[Notice]:
        """Discover all timetable notices across paginated listing pages."""
        notices: List[Notice] = []
        visited_listing_urls: Set[str] = set()
        visited_notice_urls: Set[str] = set()

        next_url = self.base_url
        page_num = 1

        while next_url and page_num <= self.max_pages:
            if next_url in visited_listing_urls:
                break
            visited_listing_urls.add(next_url)

            logger.info("Fetching listing page %d: %s", page_num, next_url)
            html = self.fetch_page(next_url)
            if not html:
                break

            soup = BeautifulSoup(html, "html.parser")

            # Look for post cards
            # In Elementor: <article class="elementor-post elementor-grid-item ...">
            articles = soup.find_all(
                "article",
                class_=lambda c: c and ("elementor-grid-item" in c or "type-post" in c),
            )
            # Filter out single page containers (like post-1533 page type-page)
            post_articles = [
                a for a in articles
                if "type-page" not in (a.get("class") or [])
            ]

            if not post_articles:
                # Fallback: look for any article with elementor-post__title
                post_articles = [
                    a for a in soup.find_all("article")
                    if a.find(class_="elementor-post__title")
                ]

            if not post_articles:
                logger.info("No more posts found on page %d", page_num)
                break

            logger.info("Found %d posts on page %d", len(post_articles), page_num)

            for art in post_articles:
                # Extract title and URL
                title_el = art.find(class_="elementor-post__title")
                title_link = title_el.find("a") if title_el else None
                if not title_link:
                    # Alternative link search
                    title_link = art.find("a", class_="elementor-post__read-more")

                if not title_link:
                    continue

                title = title_el.get_text(strip=True) if title_el else title_link.get_text(strip=True)
                notice_url = urljoin(next_url, title_link["href"])

                if notice_url in visited_notice_urls:
                    continue
                visited_notice_urls.add(notice_url)

                # Extract date
                date_el = art.find(class_="elementor-post-date")
                if not date_el:
                    date_el = art.find("time")

                raw_date = date_el.get_text(strip=True) if date_el else ""
                parsed_dt = parse_date_string(raw_date) or datetime.min
                pub_date_str = parsed_dt.strftime("%Y-%m-%d") if parsed_dt != datetime.min else "1970-01-01"

                # Fetch PDF links for this notice
                pdf_links = self.extract_pdf_links_from_notice(notice_url)
                if not pdf_links:
                    logger.warning("No PDF links found in notice: %s (%s)", title, notice_url)
                    continue

                notices.append(
                    Notice(
                        title=title,
                        url=notice_url,
                        publication_date=pub_date_str,
                        publication_datetime=parsed_dt,
                        pdf_links=pdf_links,
                    )
                )

            # Check next page
            anchor = soup.find("div", class_="e-load-more-anchor")
            max_page_attr = anchor.get("data-max-page") if anchor else None
            next_page_attr = anchor.get("data-next-page") if anchor else None

            if max_page_attr:
                try:
                    total_max = int(max_page_attr)
                    if page_num >= total_max:
                        logger.info("Reached maximum page limit declared by site (%d)", total_max)
                        break
                except ValueError:
                    pass

            page_num += 1
            if next_page_attr and next_page_attr not in visited_listing_urls:
                next_url = next_page_attr
            else:
                next_url = f"{self.base_url.rstrip('/')}/page/{page_num}/"

        return notices

    def extract_pdf_links_from_notice(self, notice_url: str) -> List[PDFLinkInfo]:
        """Fetch a notice page and extract all PDF links with their surrounding text."""
        html = self.fetch_page(notice_url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        pdf_links: List[PDFLinkInfo] = []
        seen_urls: Set[str] = set()

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if ".pdf" in href.lower():
                full_url = urljoin(notice_url, href)
                if full_url not in seen_urls:
                    seen_urls.add(full_url)
                    text = a.get_text(strip=True)
                    if not text and a.parent:
                        text = a.parent.get_text(strip=True)
                    pdf_links.append(PDFLinkInfo(url=full_url, text=text))

        return pdf_links
