from __future__ import annotations

from crawlers.base import BaseCrawler, NoticeData
from crawlers.registry import register_crawler

from .common import HTMLListMixin, RSSListMixin, categorize_notice, dedupe_notices, parse_date


@register_crawler("nipa")
class NIPACrawler(RSSListMixin, HTMLListMixin, BaseCrawler):
    agency_name = "NIPA"
    agency_code = "nipa"
    website_url = "https://www.nipa.kr"
    notice_url = "https://www.nipa.kr/home/2-2"
    rss_url = "https://www.nipa.kr/rss/notice.xml"
    crawler_method = "rss"

    def _categorize_notice(self, title: str, summary: str = "") -> str:
        return categorize_notice(title, summary, default="news")

    def _parse_date(self, date_str: str) -> str:
        return parse_date(date_str)

    def fetch_notices(self) -> list[NoticeData]:
        notices: list[NoticeData] = []
        try:
            notices.extend(self.fetch_from_rss())
        except Exception as exc:
            self.logger.info("NIPA RSS skipped: %s", exc)

        if not notices:
            try:
                notices.extend(self.fetch_from_html())
            except Exception as exc:
                self.logger.warning("NIPA HTML fallback failed: %s", exc)

        return dedupe_notices(notices)
