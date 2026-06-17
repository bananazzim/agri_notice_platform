from __future__ import annotations

import re

from crawlers.base import BaseCrawler, NoticeData
from crawlers.registry import register_crawler

from .common import HTMLListMixin, categorize_notice, dedupe_notices


@register_crawler("smb")
class SMBCrawler(HTMLListMixin, BaseCrawler):
    agency_name = "중소벤처기업부"
    agency_code = "smb"
    website_url = "https://www.mss.go.kr"
    notice_url = "https://www.mss.go.kr/site/smba/ex/bbs/List.do?cbIdx=86"
    crawler_method = "html"

    def _categorize_notice(self, title: str, summary: str = "") -> str:
        return categorize_notice(title, summary, default="support")

    def build_url_from_onclick(self, onclick: str) -> str:
        match = re.search(
            r"doBbsFView\(['\"]?([^,'\"]+)['\"]?,\s*['\"]?([^,'\"]+)['\"]?,"
            r"\s*['\"]?([^,'\"]+)['\"]?,\s*['\"]?([^,'\"]+)['\"]?\)",
            onclick,
        )
        if not match:
            return ""

        cb_idx, bc_idx, _menu_code, parent_seq = match.groups()
        return (
            f"{self.website_url}/site/smba/ex/bbs/View.do"
            f"?cbIdx={cb_idx}&bcIdx={bc_idx}&parentSeq={parent_seq}"
        )

    def fetch_notices(self) -> list[NoticeData]:
        try:
            return dedupe_notices(self.fetch_from_html())
        except Exception as exc:
            self.logger.warning("MSS HTML crawl failed: %s", exc)
            return []
