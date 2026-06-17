from __future__ import annotations

from crawlers.base import BaseCrawler, NoticeData
from crawlers.registry import register_crawler

from .common import HTMLListMixin, RSSListMixin, categorize_notice, dedupe_notices, parse_date


@register_crawler("mafra")
class MAFRACrawler(RSSListMixin, HTMLListMixin, BaseCrawler):
    agency_name = "농림축산식품부"
    agency_code = "mafra"
    website_url = "https://www.mafra.go.kr"
    notice_url = "https://www.mafra.go.kr/home/5109/subview.do"
    rss_url = "https://www.mafra.go.kr/rss/newsList.xml"
    api_url = "https://www.mafra.go.kr"
    crawler_method = "rss"

    def _categorize_notice(self, title: str, summary: str = "") -> str:
        text = f"{title} {summary}".lower()
        if any(keyword in text for keyword in ("지원사업", "사업공고", "지원계획", "보조", "융자", "자금")):
            return "support"
        return categorize_notice(title, summary, default="news")

    def _parse_rss_date(self, date_str: str) -> str:
        return parse_date(date_str)

    def _parse_rss_feed(self) -> list[NoticeData]:
        return self.fetch_from_rss()

    def _fetch_from_website(self) -> list[NoticeData]:
        return self.fetch_from_html()

    def fetch_notices(self) -> list[NoticeData]:
        notices: list[NoticeData] = []

        try:
            notices.extend(self._parse_rss_feed())
        except Exception as exc:
            self.logger.info("MAFRA RSS skipped: %s", exc)

        try:
            notices.extend(self._fetch_from_website())
        except Exception as exc:
            self.logger.warning("MAFRA HTML fallback failed: %s", exc)

        return dedupe_notices(notices)
