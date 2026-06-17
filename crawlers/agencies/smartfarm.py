from __future__ import annotations

import re

from crawlers.base import BaseCrawler, NoticeData
from crawlers.registry import register_crawler

from .common import HTMLListMixin, RSSListMixin, categorize_notice, dedupe_notices, parse_date


@register_crawler("smartfarm")
class SmartFarmCrawler(RSSListMixin, HTMLListMixin, BaseCrawler):
    agency_name = "스마트팜코리아"
    agency_code = "smartfarm"
    website_url = "https://www.smartfarmkorea.net"
    notice_url = "https://www.smartfarmkorea.net/board/list.do?menuId=M110502"
    rss_url = "https://www.smartfarmkorea.net/rss/notice.xml"
    crawler_method = "html"

    def _categorize_notice(self, title: str, summary: str = "") -> str:
        return categorize_notice(title, summary, default="news")

    def _parse_date(self, date_str: str) -> str:
        return parse_date(date_str)

    def build_url_from_onclick(self, onclick: str) -> str:
        match = re.search(r"boardView\(['\"]?(\d+)['\"]?\)", onclick)
        if not match:
            return ""
        return (
            f"{self.website_url}/board/view.do?"
            f"menuId=M110502&searchBbsId=BBSMSTR_000000000021&searchNttId={match.group(1)}"
        )

    def fetch_notices(self) -> list[NoticeData]:
        notices: list[NoticeData] = []
        try:
            notices.extend(self.fetch_from_rss())
        except Exception as exc:
            self.logger.info("SmartFarm RSS skipped: %s", exc)

        try:
            notices.extend(self.fetch_from_html(self.notice_url))
        except Exception as exc:
            self.logger.warning("SmartFarm HTML fallback failed: %s", exc)

        return dedupe_notices(notices)
