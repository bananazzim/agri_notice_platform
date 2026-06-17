from __future__ import annotations

import os
from typing import Any
from xml.etree import ElementTree as ET

from django.conf import settings

from crawlers.base import BaseCrawler, NoticeData
from crawlers.registry import register_crawler
from core.exceptions import CrawlerConnectionError, CrawlerParseError

from .common import HTMLListMixin, categorize_notice, dedupe_notices, enrich_notice_from_detail


@register_crawler("bizinfo")
class BizinfoCrawler(HTMLListMixin, BaseCrawler):
    agency_name = "기업마당"
    agency_code = "bizinfo"
    website_url = "https://www.bizinfo.go.kr"
    notice_url = "https://www.bizinfo.go.kr/web/lay1/bbs/S1T122C128/AS/74/list.do"
    api_url = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
    crawler_method = "api"

    SUPPORT_API = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"

    def __init__(self) -> None:
        super().__init__()
        self.api_key = (
            getattr(settings, "BIZINFO_API_KEY", None)
            or os.getenv("BIZINFO_API_KEY")
            or ""
        )

    def _fetch_support_info(self, page: int = 1, page_size: int = 50) -> str:
        params = {
            "pageUnit": page_size,
            "pageIndex": page,
            "dataType": "xml",
        }
        if self.api_key:
            params["serviceKey"] = self.api_key

        try:
            response = self.fetch_page(self.SUPPORT_API, params=params)
            return response.text
        except CrawlerConnectionError:
            raise
        except Exception as exc:
            raise CrawlerConnectionError(f"Bizinfo API request failed: {exc}") from exc

    def _parse_xml_response(self, xml_str: str) -> list[dict[str, str]]:
        try:
            root = ET.fromstring(xml_str)
        except ET.ParseError as exc:
            raise CrawlerParseError(f"Bizinfo XML parse failed: {exc}") from exc

        items: list[dict[str, str]] = []
        for item in root.findall(".//item"):
            parsed: dict[str, str] = {}
            for child in item:
                tag = child.tag.split("}")[-1]
                parsed[tag] = child.text or ""
            items.append(parsed)
        return items

    def _parse_api_item(self, item: dict[str, Any]) -> NoticeData:
        title = item.get("pblancNm") or item.get("bizTitle") or item.get("title") or ""
        summary = item.get("bsnsSumryCn") or item.get("bizSummary") or item.get("summary") or ""
        url = item.get("pblancUrl") or item.get("bizUrl") or item.get("link") or self.notice_url

        notice = {
            "agency": self.agency_code,
            "title": title,
            "content": summary,
            "summary": summary,
            "url": url,
            "posted_date": item.get("creatPnttm") or item.get("bizRegistDt") or item.get("date"),
            "deadline": (
                item.get("reqstEndDe")
                or item.get("reqstEndDate")
                or item.get("rceptEndDe")
                or item.get("rceptClosDe")
                or item.get("pblancEndDate")
                or item.get("bizDeadline")
                or item.get("endDate")
            ),
            "category": self._categorize_notice(
                item.get("pldirSportRealmLclasCodeNm", "")
                or item.get("bizType", "")
                or title
            ),
        }
        return enrich_notice_from_detail(self, notice)

    def _categorize_notice(self, notice_type: str) -> str:
        return categorize_notice(notice_type, default="support")

    def _fetch_from_website(self) -> list[NoticeData]:
        return self.fetch_from_html()

    def fetch_notices(self) -> list[NoticeData]:
        notices: list[NoticeData] = []

        try:
            items = self._parse_xml_response(self._fetch_support_info())
            notices.extend(self._parse_api_item(item) for item in items)
        except Exception as exc:
            self.logger.info("Bizinfo API skipped, using HTML fallback: %s", exc)

        try:
            notices.extend(self._fetch_from_website())
        except Exception as exc:
            self.logger.warning("Bizinfo HTML fallback failed: %s", exc)

        return dedupe_notices([notice for notice in notices if notice.get("title")])
