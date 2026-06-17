from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import unquote

from bs4 import Tag

from crawlers.base import BaseCrawler, NoticeData
from crawlers.registry import register_crawler

from .common import HTMLListMixin, categorize_notice, dedupe_notices, first_regex, parse_date


@register_crawler("startup")
class StartupCrawler(HTMLListMixin, BaseCrawler):
    agency_name = "창업진흥원 K-Startup"
    agency_code = "startup"
    website_url = "https://www.k-startup.go.kr"
    notice_url = "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do"
    api_url = (
        "https://nidview.k-startup.go.kr/view/public/call/"
        "kisedKstartupService/announcementInformation"
    )
    crawler_method = "api"
    api_page_size = 50

    def _categorize_notice(self, title: str, summary: str = "") -> str:
        return categorize_notice(title, summary, default="startup")

    def _repair_text(self, value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return ""

        mojibake_markers = ("ì", "ë", "í", "ê", "ã", "â", "ï")
        if not any(marker in text for marker in mojibake_markers):
            return text

        try:
            repaired = text.encode("latin1").decode("utf-8")
        except UnicodeError:
            return text

        return repaired if repaired else text

    def _format_detail_url(self, pbanc_sn: Any) -> str:
        if not pbanc_sn:
            return self.notice_url
        return f"{self.notice_url}?schM=view&pbancSn={pbanc_sn}"

    def _parse_api_item(self, item: dict[str, Any]) -> NoticeData | None:
        title = self._repair_text(item.get("biz_pbanc_nm") or item.get("intg_pbanc_biz_nm"))
        if not title:
            return None

        summary_parts = [
            item.get("pbanc_ctnt"),
            item.get("aply_trgt_ctnt"),
            item.get("supt_regin"),
            item.get("aply_trgt"),
        ]
        summary = " ".join(self._repair_text(part) for part in summary_parts if part)
        url = self._repair_text(item.get("detl_pg_url")) or self._format_detail_url(
            item.get("pbanc_sn")
        )
        category = self._repair_text(item.get("supt_biz_clsfc"))

        return {
            "agency": self.agency_code,
            "title": title,
            "url": url,
            "posted_date": parse_date(item.get("pbanc_rcpt_bgng_dt")),
            "deadline": parse_date(item.get("pbanc_rcpt_end_dt")),
            "category": self._categorize_notice(category, summary),
            "summary": summary,
            "content": summary,
        }

    def fetch_from_api(self) -> list[NoticeData]:
        params: dict[str, Any] = {
            "page": 1,
            "perPage": self.api_page_size,
            "cond[rcrt_prgs_yn::EQ]": "Y",
        }
        api_key = os.getenv("KSTARTUP_API_KEY") or os.getenv("DATA_GO_KR_API_KEY")
        if api_key:
            params["serviceKey"] = unquote(api_key)

        response = self.fetch_page(
            self.api_url,
            params=params,
            headers={"Accept": "application/json"},
        )
        response.encoding = "utf-8"
        payload = response.json()
        notices: list[NoticeData] = []
        for item in payload.get("data", []):
            if isinstance(item, dict):
                notice = self._parse_api_item(item)
                if notice:
                    notices.append(notice)
        return notices

    def _parse_card(self, card: Tag) -> NoticeData | None:
        title_el = card.select_one(".tit")
        if title_el is None:
            return None

        title = title_el.get_text(" ", strip=True)
        text = card.get_text(" ", strip=True)
        link = None
        for candidate in card.select("a[href], a[onclick]"):
            candidate_ref = " ".join(
                [
                    candidate.get("href", ""),
                    candidate.get("onclick", ""),
                ]
            )
            if "go_view" in candidate_ref:
                link = candidate
                break
        link_ref = " ".join([link.get("href", ""), link.get("onclick", "")]) if link else ""
        match = re.search(r"go_view\((\d+)\)", link_ref)
        url = self.notice_url
        if match:
            url = f"{self.notice_url}?schM=view&pbancSn={match.group(1)}"

        category = ""
        flag = card.select_one(".flag")
        if flag:
            category = flag.get_text(" ", strip=True)

        return {
            "agency": self.agency_code,
            "title": title,
            "url": url,
            "posted_date": first_regex(r"등록일자\s*(\d{4}-\d{2}-\d{2})", text),
            "deadline": first_regex(r"마감일자\s*(\d{4}-\d{2}-\d{2})", text),
            "category": self._categorize_notice(category, title),
            "summary": text,
            "content": text,
        }

    def _fetch_from_static_html(self) -> list[NoticeData]:
        response = self.fetch_page(self.notice_url)
        soup = self.parse_html(response.text)
        notices: list[NoticeData] = []
        for card in soup.select(".board_list-wrap li.notice"):
            if isinstance(card, Tag):
                notice = self._parse_card(card)
                if notice:
                    notices.append(notice)
        return notices

    def fetch_notices(self) -> list[NoticeData]:
        notices: list[NoticeData] = []

        try:
            notices.extend(self.fetch_from_api())
        except Exception as exc:
            self.logger.info("K-Startup API skipped: %s", exc)

        if notices:
            return dedupe_notices(notices)

        try:
            notices.extend(self._fetch_from_static_html())
        except Exception as exc:
            self.logger.info("K-Startup static HTML skipped: %s", exc)

        if notices:
            return dedupe_notices(notices)

        try:
            html = self.render_js_page(self.notice_url)
            soup = self.parse_html(html)
            notices.extend(self.parse_html_list(soup))
        except Exception as exc:
            self.logger.info("K-Startup Playwright skipped: %s", exc)
            try:
                notices.extend(self.fetch_from_html())
            except Exception as html_exc:
                self.logger.warning("K-Startup HTML fallback failed: %s", html_exc)

        return dedupe_notices(notices)
