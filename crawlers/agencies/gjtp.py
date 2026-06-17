from __future__ import annotations

from crawlers.base import BaseCrawler, NoticeData
from crawlers.registry import register_crawler

from .common import HTMLListMixin, categorize_notice, dedupe_notices


@register_crawler("gjtp")
class GJTPCrawler(HTMLListMixin, BaseCrawler):
    agency_name = "광주테크노파크"
    agency_code = "gjtp"
    website_url = "https://www.gjtp.or.kr"
    notice_url = "https://www.gjtp.or.kr/board/B0008.cs?act=list&m=14"
    crawler_method = "html"

    def _categorize_notice(self, title: str, summary: str = "") -> str:
        return categorize_notice(title, summary, default="support")

    def fetch_notices(self) -> list[NoticeData]:
        try:
            return dedupe_notices(self.fetch_from_html())
        except Exception as exc:
            self.logger.warning("GJTP HTML crawl failed: %s", exc)
            return []
