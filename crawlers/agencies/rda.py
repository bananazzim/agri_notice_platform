from __future__ import annotations

from typing import Any

import requests

from crawlers.base import BaseCrawler, NoticeData
from crawlers.registry import register_crawler
from core.exceptions import CrawlerConnectionError, CrawlerParseError

from .common import HTMLListMixin, categorize_notice, dedupe_notices


@register_crawler("rda")
class RDACrawler(HTMLListMixin, BaseCrawler):
    agency_name = "농촌진흥청"
    agency_code = "rda"
    website_url = "https://www.rda.go.kr"
    notice_url = "https://www.rda.go.kr/board/board.do?mode=list&prgId=nei_ancmttEntry"
    api_url = "https://www.rda.go.kr/api"
    crawler_method = "api"

    SUPPORT_ENDPOINT = "https://www.rda.go.kr/api/support/list"
    NEWS_ENDPOINT = "https://www.rda.go.kr/api/news/list"
    NOTICE_ENDPOINT = "https://www.rda.go.kr/api/notice/list"

    api_endpoints = (SUPPORT_ENDPOINT, NEWS_ENDPOINT, NOTICE_ENDPOINT)

    def _fetch_from_api(
        self,
        endpoint: str,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        try:
            response = self.fetch_page(
                endpoint,
                params={"page": page, "pageSize": page_size, "sort": "DESC"},
            )
            data = response.json()
        except requests.exceptions.JSONDecodeError as exc:
            raise CrawlerParseError(f"RDA API returned invalid JSON: {exc}") from exc
        except CrawlerConnectionError:
            raise
        except Exception as exc:
            raise CrawlerParseError(f"RDA API request failed: {exc}") from exc

        if isinstance(data, dict) and (data.get("success") or "list" in data or "items" in data):
            return data

        raise CrawlerParseError(f"Unexpected RDA API response: {data}")

    def _parse_api_notice(self, item: dict[str, Any]) -> NoticeData:
        title = item.get("title") or item.get("subject") or item.get("nttSj") or ""
        content = item.get("content") or item.get("body") or item.get("summary") or ""
        url = item.get("url") or item.get("link") or item.get("detailUrl") or self.notice_url

        return {
            "agency": self.agency_code,
            "title": title,
            "content": content,
            "summary": item.get("summary", ""),
            "url": url,
            "posted_date": item.get("createdDate") or item.get("date") or item.get("regDate"),
            "deadline": item.get("deadline") or item.get("endDate"),
            "category": self._categorize_notice(item.get("category", ""), title),
        }

    def _categorize_notice(self, category_str: str = "", title: str = "") -> str:
        return categorize_notice(category_str, title, default="support")

    def fetch_notices(self) -> list[NoticeData]:
        notices: list[NoticeData] = []

        for endpoint in self.api_endpoints:
            try:
                data = self._fetch_from_api(endpoint)
            except Exception as exc:
                self.logger.info("RDA API endpoint skipped: %s (%s)", endpoint, exc)
                continue

            items = data.get("list") or data.get("items") or []
            for item in items:
                notice = self._parse_api_notice(item)
                if notice.get("title") and notice.get("url"):
                    notices.append(notice)

        if not notices:
            try:
                notices.extend(self.fetch_from_html())
            except Exception as exc:
                self.logger.warning("RDA HTML fallback failed: %s", exc)

        return dedupe_notices(notices)
