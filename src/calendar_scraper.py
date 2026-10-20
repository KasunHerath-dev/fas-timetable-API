"""Web scraper for FAS WUSL Academic Calendar notices and PDF links."""

import logging
import re
from datetime import datetime
from typing import List, Optional, Set
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .config import DEFAULT_CALENDAR_BASE_URL, DEFAULT_USER_AGENT, DEFAULT_MAX_PAGES, REQUEST_TIMEOUT
from .calendar_models import DiscoveredCalendarLink
from .scraper import parse_date_string

logger = logging.getLogger(__name__)


class AcademicCalendarScraper:
    """Scrapes official FAS academic calendar notices and resolves downloadable PDF links."""

    def __init__(
        self,
        base_url: str = DEFAULT_CALENDAR_BASE_URL,
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

    def discover_calendar_links(self) -> List[DiscoveredCalendarLink]:
        """Discover all academic calendar PDF documents from the official listing and notice pages."""
        discovered: List[DiscoveredCalendarLink] = []
        visited_listing_urls: Set[str] = set()
        visited_notice_urls: Set[str] = set()
        seen_pdf_urls: Set[str] = set()

        next_url = self.base_url
        page_num = 1

        while next_url and page_num <= self.max_pages:
            if next_url in visited_listing_urls:
                break
            visited_listing_urls.add(next_url)

            logger.info("Fetching calendar listing page %d: %s", page_num, next_url)
            html = self.fetch_page(next_url)
            if not html:
                break

            soup = BeautifulSoup(html, "html.parser")

            # Look for post cards
            articles = soup.find_all(
                "article",
                class_=lambda c: c and ("elementor-grid-item" in c or "type-post" in c),
            )
            post_articles = [
                a for a in articles
                if "type-page" not in (a.get("class") or [])
            ]

            if not post_articles:
                # Fallback: look for any article or container with post title
                post_articles = [
                    a for a in soup.find_all(["article", "div"])
                    if a.find(class_=lambda c: c and "title" in c) and a.find("a", href=True)
                ]

            if not post_articles:
                # Second fallback: look for direct PDF links on the listing page
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    if ".pdf" in href.lower() and any(k in href.lower() or k in a.text.lower() for k in ["cod", "calendar", "date"]):
                        full_pdf_url = urljoin(next_url, href)
                        if full_pdf_url not in seen_pdf_urls:
                            seen_pdf_urls.add(full_pdf_url)
                            discovered.append(
                                DiscoveredCalendarLink(
                                    noticeTitle=a.get_text(strip=True) or "Academic Calendar Notice",
                                    noticeUrl=next_url,
                                    publicationDate=None,
                                    pdfUrl=full_pdf_url,
                                    linkText=a.get_text(strip=True),
                                )
                            )

            for art in post_articles:
                # Extract title and link
                title_el = art.find(class_=lambda c: c and ("title" in c or "post__title" in c))
                title_link = title_el.find("a") if title_el else None
                if not title_link:
                    title_link = art.find("a", class_=lambda c: c and "read-more" in c)
                if not title_link:
                    title_link = art.find("a", href=True)

                if not title_link:
                    continue

                raw_title = title_el.get_text(strip=True) if title_el else title_link.get_text(strip=True)
                notice_url = urljoin(next_url, title_link["href"])

                # Check if notice relates to calendar of dates or academic calendar
                title_lower = raw_title.lower()
                href_lower = notice_url.lower()
                if not any(k in title_lower or k in href_lower for k in ["calendar", "dates", "cod", "academic"]):
                    continue

                if notice_url in visited_notice_urls:
                    continue
                visited_notice_urls.add(notice_url)

                # Extract publication date
                date_el = art.find(class_=lambda c: c and ("date" in c or "time" in c))
                if not date_el:
                    date_el = art.find("time")

                raw_date = date_el.get_text(strip=True) if date_el else ""
                parsed_dt = parse_date_string(raw_date)
                pub_date_str = parsed_dt.strftime("%Y-%m-%d") if parsed_dt else None

                # Visit individual notice page to find the PDF link
                pdf_links = self.extract_pdf_links_from_notice(notice_url)

                # If notice page itself had a <time> tag and card didn't, try extracting date from notice page
                if not pub_date_str and pdf_links:
                    notice_html = self.fetch_page(notice_url)
                    if notice_html:
                        nsoup = BeautifulSoup(notice_html, "html.parser")
                        ntime = nsoup.find("time")
                        if ntime:
                            ndt = parse_date_string(ntime.get_text(strip=True))
                            if ndt:
                                parsed_dt = ndt
                                pub_date_str = ndt.strftime("%Y-%m-%d")

                for plink in pdf_links:
                    if plink["url"] not in seen_pdf_urls:
                        seen_pdf_urls.add(plink["url"])
                        discovered.append(
                            DiscoveredCalendarLink(
                                noticeTitle=raw_title,
                                noticeUrl=notice_url,
                                publicationDate=pub_date_str,
                                publicationDatetime=parsed_dt,
                                pdfUrl=plink["url"],
                                linkText=plink["text"],
                            )
                        )

            # Check next page pagination
            anchor = soup.find("div", class_="e-load-more-anchor")
            max_page_attr = anchor.get("data-max-page") if anchor else None
            next_page_attr = anchor.get("data-next-page") if anchor else None

            if max_page_attr:
                try:
                    total_max = int(max_page_attr)
                    if page_num >= total_max:
                        break
                except ValueError:
                    pass

            page_num += 1
            if next_page_attr and next_page_attr not in visited_listing_urls:
                next_url = next_page_attr
            elif anchor and anchor.find("a", href=True):
                next_url = anchor.find("a")["href"]
            else:
                next_url = None

        logger.info("Discovered %d academic calendar PDF links.", len(discovered))
        return discovered

    def extract_pdf_links_from_notice(self, notice_url: str) -> List[dict]:
        """Fetch an individual notice page and extract PDF links with descriptive anchor text."""
        html = self.fetch_page(notice_url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        pdf_links: List[dict] = []
        seen: Set[str] = set()

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if ".pdf" in href.lower():
                full_url = urljoin(notice_url, href)
                if full_url not in seen:
                    seen.add(full_url)
                    text = a.get_text(strip=True)
                    if not text and a.parent:
                        text = a.parent.get_text(strip=True)
                    pdf_links.append({"url": full_url, "text": text})

        return pdf_links
