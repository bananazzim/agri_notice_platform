from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup
from django.utils import timezone
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.exceptions import (
    CrawlerConnectionError,
    CrawlerException,
    CrawlerNotImplementedError,
    CrawlerParseError,
)
from core.logger import get_crawler_logger
from core.utils import clean_text, is_deadline_soon, normalize_date, normalize_url

NoticeData = dict[str, Any]
CrawlerResult = dict[str, Any]


class BaseCrawler(ABC):
    """Common interface and utilities for all agency crawlers."""

    agency_name: str = "Unknown"
    agency_code: str = "unknown"
    website_url: str = ""
    notice_url: str = ""
    api_url: str = ""
    rss_url: str = ""

    crawler_method: str = "html"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0

    required_fields: tuple[str, ...] = ("title", "url", "posted_date")

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36",
    ]

    def __init__(self) -> None:
        self.logger = get_crawler_logger(self.agency_code)
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        retry_strategy = Retry(
            total=self.max_retries,
            connect=self.max_retries,
            read=self.max_retries,
            status=self.max_retries,
            backoff_factor=self.retry_delay,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("HEAD", "GET", "OPTIONS"),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)

        session = requests.Session()
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update(
            {
                "User-Agent": self._get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.6",
            }
        )
        return session

    def _get_random_user_agent(self) -> str:
        return random.choice(self.USER_AGENTS)

    def _update_user_agent(self) -> None:
        self.session.headers["User-Agent"] = self._get_random_user_agent()

    def fetch_page(self, url: str, **kwargs: Any) -> requests.Response:
        if not url:
            raise CrawlerConnectionError("Cannot fetch an empty URL.")

        try:
            self._update_user_agent()
            response = self.session.get(url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            self.logger.debug("Fetched page: %s", url)
            return response
        except requests.RequestException as exc:
            self.logger.warning("Failed to fetch %s: %s", url, exc)
            raise CrawlerConnectionError(f"Failed to fetch {url}: {exc}") from exc

    def parse_html(self, html: str, parser: str = "html.parser") -> BeautifulSoup:
        if not html:
            raise CrawlerParseError("Cannot parse empty HTML.")

        try:
            return BeautifulSoup(html, parser)
        except Exception as exc:
            raise CrawlerParseError(f"Failed to parse HTML: {exc}") from exc

    def parse_rss(self, rss_url: str) -> Any:
        try:
            response = self.fetch_page(rss_url)
            feed = feedparser.parse(response.content)
        except CrawlerConnectionError:
            raise
        except Exception as exc:
            raise CrawlerParseError(f"Failed to parse RSS feed: {exc}") from exc

        if getattr(feed, "bozo", False):
            self.logger.warning("RSS parse warning for %s: %s", rss_url, feed.bozo_exception)

        return feed

    def render_js_page(
        self,
        url: str,
        wait_until: str = "networkidle",
        timeout: int | None = None,
    ) -> str:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise CrawlerParseError("Playwright is not installed.") from exc

        timeout_ms = (timeout or self.timeout) * 1000

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until=wait_until, timeout=timeout_ms)
                html = page.content()
                browser.close()
                return html
        except Exception as exc:
            raise CrawlerParseError(f"Failed to render JS page {url}: {exc}") from exc

    def get_entry_value(self, entry: Any, key: str, default: Any = "") -> Any:
        if hasattr(entry, "get") and callable(entry.get):
            try:
                return entry.get(key, default)
            except Exception:
                pass
        return getattr(entry, key, default)

    def to_absolute_url(self, url: str, base_url: str | None = None) -> str:
        base = base_url or self.website_url or self.notice_url
        return normalize_url(urljoin(base, url), base)

    def select_text(self, soup: BeautifulSoup, selector: str, default: str = "") -> str:
        element = soup.select_one(selector)
        if element is None:
            return default
        return clean_text(element.get_text(" ", strip=True))

    def select_attr(
        self,
        soup: BeautifulSoup,
        selector: str,
        attr: str,
        default: str = "",
    ) -> str:
        element = soup.select_one(selector)
        if element is None:
            return default
        return clean_text(element.get(attr, default))

    @abstractmethod
    def fetch_notices(self) -> list[NoticeData]:
        raise CrawlerNotImplementedError(
            f"{self.__class__.__name__} must implement fetch_notices()."
        )

    def normalize_notice(self, notice: NoticeData) -> NoticeData:
        posted_date = normalize_date(notice.get("posted_date"))
        deadline = normalize_date(notice.get("deadline"))

        return {
            "agency": notice.get("agency") or self.agency_code,
            "title": clean_text(notice.get("title", "")),
            "url": self.to_absolute_url(notice.get("url", "")),
            "posted_date": posted_date,
            "deadline": deadline,
            "category": clean_text(notice.get("category", "other")) or "other",
            "summary": clean_text(notice.get("summary", "")),
            "content": clean_text(notice.get("content", "")),
            "is_deadline_soon": is_deadline_soon(deadline),
            "importance_score": int(notice.get("importance_score") or 50),
            "ai_tags": list(notice.get("ai_tags") or []),
            "recommended_for": list(notice.get("recommended_for") or []),
        }

    def validate_notice(self, notice: NoticeData) -> bool:
        for field in self.required_fields:
            if not notice.get(field):
                self.logger.warning("Missing required field %s: %s", field, notice)
                return False

        url = str(notice.get("url", ""))
        if not url.startswith(("http://", "https://")):
            self.logger.warning("Invalid notice URL: %s", url)
            return False

        if len(str(notice.get("title", ""))) > 500:
            notice["title"] = str(notice["title"])[:500]

        return True

    def crawl(self) -> CrawlerResult:
        started_at = timezone.now()
        result: CrawlerResult = {
            "status": "success",
            "agency": self.agency_code,
            "notices": [],
            "count": 0,
            "error": "",
            "start_time": started_at,
        }

        try:
            self.logger.info("Crawler started: %s (%s)", self.agency_name, self.agency_code)
            raw_notices = self.fetch_notices()
            valid_notices: list[NoticeData] = []

            for raw_notice in raw_notices:
                try:
                    normalized = self.normalize_notice(raw_notice)
                    if self.validate_notice(normalized):
                        valid_notices.append(normalized)
                except Exception as exc:
                    self.logger.warning(
                        "Failed to normalize notice from %s: %s",
                        self.agency_code,
                        exc,
                        exc_info=True,
                    )

            result["notices"] = valid_notices
            result["count"] = len(valid_notices)

            if len(valid_notices) < len(raw_notices):
                result["status"] = "partial"

            self.logger.info(
                "Crawler finished: %s collected=%s valid=%s",
                self.agency_code,
                len(raw_notices),
                len(valid_notices),
            )
        except CrawlerException as exc:
            result["status"] = "failed"
            result["error"] = str(exc)
            self.logger.error("Crawler failed: %s - %s", self.agency_code, exc, exc_info=True)
        except Exception as exc:
            result["status"] = "failed"
            result["error"] = f"Unexpected error: {exc}"
            self.logger.error("Crawler crashed: %s - %s", self.agency_code, exc, exc_info=True)
        finally:
            ended_at = timezone.now()
            result["end_time"] = ended_at
            result["duration"] = (ended_at - started_at).total_seconds()

        return result

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "BaseCrawler":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def __str__(self) -> str:
        return f"{self.agency_name} ({self.agency_code})"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.agency_code}>"
