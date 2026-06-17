from __future__ import annotations

from crawlers.base import BaseCrawler, NoticeData
from crawlers.registry import register_crawler

from .common import HTMLListMixin, categorize_notice, dedupe_notices


@register_crawler("jbtp")
class JBTPCrawler(HTMLListMixin, BaseCrawler):
    agency_name = "전북테크노파크"
    agency_code = "jbtp"
    website_url = "https://rnd.jbtp.or.kr"
    notice_url = "https://rnd.jbtp.or.kr/main/menu?gc=605XOAS"
    crawler_method = "html"

    def _categorize_notice(self, title: str, summary: str = "") -> str:
        return categorize_notice(title, summary, default="support")

    def fetch_notices(self) -> list[NoticeData]:
        try:
            return dedupe_notices(self.fetch_from_html())
        except Exception as exc:
            self.logger.warning("JBTP HTML crawl failed: %s", exc)
            return []
