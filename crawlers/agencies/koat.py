from __future__ import annotations

import re

from crawlers.base import BaseCrawler, NoticeData
from crawlers.registry import register_crawler

from .common import HTMLListMixin, RSSListMixin, categorize_notice, dedupe_notices, parse_date


@register_crawler("koat")
class KOATCrawler(RSSListMixin, HTMLListMixin, BaseCrawler):
    agency_name = "한국농업기술진흥원"
    agency_code = "koat"
    website_url = "https://www.koat.or.kr"
    notice_url = "https://www.koat.or.kr/board/business/list.do"
    rss_url = "https://www.koat.or.kr/rss/notice.xml"
    crawler_method = "html"
    html_urls = (
        ("business", "https://www.koat.or.kr/board/business/list.do"),
        ("notice", "https://www.koat.or.kr/board/notice/list.do"),
    )

    def _categorize_notice(self, title: str, summary: str = "") -> str:
        return categorize_notice(title, summary, default="support")

    def _parse_date(self, date_str: str) -> str:
        return parse_date(date_str)

    def build_url_from_onclick(self, onclick: str) -> str:
        match = re.search(r"postLink\((\d+)\)", onclick)
        if not match:
            return ""
        board = getattr(self, "_current_board", "business")
        return f"{self.website_url}/board/{board}/{match.group(1)}/view.do"

    def fetch_notices(self) -> list[NoticeData]:
        notices: list[NoticeData] = []
        try:
            notices.extend(self.fetch_from_rss())
        except Exception as exc:
            self.logger.info("KOAT RSS skipped: %s", exc)

        for board, url in self.html_urls:
            try:
                self._current_board = board
                notices.extend(self.fetch_from_html(url))
            except Exception as exc:
                self.logger.warning("KOAT %s HTML fallback failed: %s", board, exc)

        return dedupe_notices(notices)
