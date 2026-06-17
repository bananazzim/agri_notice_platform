from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from crawlers.base import BaseCrawler, NoticeData
from core.utils import clean_text, normalize_date


CATEGORY_KEYWORDS = {
    "rd": ("r&d", "rd", "연구", "기술개발", "실증", "개발", "과제"),
    "startup": ("창업", "스타트업", "예비창업", "초기창업", "사업화"),
    "education": ("교육", "훈련", "강의", "과정", "아카데미", "세미나", "설명회"),
    "contest": ("공모", "경진", "대회", "콘테스트", "챌린지", "모집공고"),
    "support": ("지원", "사업", "자금", "보조", "융자", "바우처", "컨설팅", "참여기업", "모집"),
}

DATE_PATTERN = re.compile(
    r"(?P<year>\d{4})\s*(?:[.\-/년])\s*(?P<month>\d{1,2})\s*(?:[.\-/월])\s*(?P<day>\d{1,2})\s*(?:일)?"
)
COMPACT_DATE_PATTERN = re.compile(r"(?<!\d)(?P<date>\d{8})(?!\d)")
DATE_RANGE_PATTERN = re.compile(
    r"(?P<year1>\d{4})\s*(?:[.\-/년])\s*(?P<month1>\d{1,2})\s*(?:[.\-/월])\s*(?P<day1>\d{1,2})\s*(?:일)?"
    r".{0,20}?(?:~|부터|[-–—]|→)"
    r".{0,20}?(?:(?P<year2>\d{4})\s*(?:[.\-/년])\s*)?(?P<month2>\d{1,2})\s*(?:[.\-/월])\s*(?P<day2>\d{1,2})\s*(?:일)?"
)
DEADLINE_LABELS = (
    "마감",
    "마감일",
    "접수마감",
    "신청마감",
    "접수 종료",
    "접수종료",
    "신청 종료",
    "신청종료",
    "종료일",
)
PERIOD_LABELS = (
    "참가 접수",
    "접수기간",
    "신청기간",
    "공고기간",
    "모집기간",
    "지원기간",
    "사업기간",
    "접수 기간",
    "신청 기간",
    "접수",
    "신청",
)
OPEN_ENDED_KEYWORDS = ("상시", "예산 소진", "예산소진", "소진시", "별도 공지")


def categorize_notice(*values: str, default: str = "news") -> str:
    text = " ".join(value or "" for value in values).lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category
    return default


def parse_date(value: Any) -> str:
    if value is None:
        return ""

    text = clean_text(str(value))
    if not text:
        return ""

    normalized = normalize_date(text)
    if normalized:
        return normalized

    try:
        return parsedate_to_datetime(text).strftime("%Y-%m-%d")
    except Exception:
        pass

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except Exception:
        return text[:10] if len(text) >= 10 else ""


def format_date_parts(year: str | int, month: str | int, day: str | int) -> str:
    try:
        return datetime(int(year), int(month), int(day)).strftime("%Y-%m-%d")
    except ValueError:
        return ""


def find_dates_with_positions(text: str) -> list[tuple[str, int, int]]:
    dates: list[tuple[str, int, int]] = []
    for match in DATE_PATTERN.finditer(text):
        year = int(match.group("year"))
        month = int(match.group("month"))
        day = int(match.group("day"))
        try:
            normalized = datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            continue
        dates.append((normalized, match.start(), match.end()))

    for match in COMPACT_DATE_PATTERN.finditer(text):
        normalized = parse_date(match.group("date"))
        if normalized:
            dates.append((normalized, match.start(), match.end()))

    return sorted(dates, key=lambda item: item[1])


def extract_deadline_from_text(text: str) -> str:
    cleaned = clean_text(text)
    if not cleaned:
        return ""

    for match in DATE_RANGE_PATTERN.finditer(cleaned):
        window = cleaned[max(0, match.start() - 60):match.end() + 30]
        if any(keyword in window for keyword in OPEN_ENDED_KEYWORDS):
            continue
        if any(label in window for label in PERIOD_LABELS):
            end_year = match.group("year2") or match.group("year1")
            deadline = format_date_parts(end_year, match.group("month2"), match.group("day2"))
            if deadline:
                return deadline

    dates = find_dates_with_positions(cleaned)
    if not dates:
        return ""

    for date_value, start, _ in dates:
        window = cleaned[max(0, start - 45):start + 15]
        if any(label in window for label in DEADLINE_LABELS):
            return date_value

    for index, (_, first_start, first_end) in enumerate(dates[:-1]):
        second_date, second_start, _ = dates[index + 1]
        window = cleaned[max(0, first_start - 60):min(len(cleaned), second_start + 30)]
        between = cleaned[first_end:second_start]
        has_period_label = any(label in window for label in PERIOD_LABELS)
        has_range_separator = any(separator in between for separator in ("~", "-", "부터", "까지", "→"))
        is_open_ended = any(keyword in window for keyword in OPEN_ENDED_KEYWORDS)
        if has_period_label and has_range_separator and not is_open_ended:
            return second_date

    return ""


def extract_detail_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for element in soup.select("script, style, noscript"):
        element.decompose()

    selectors = (
        ".view",
        ".view-content",
        ".board-view",
        ".board_view",
        ".bbs-view",
        ".bbs_view",
        ".content",
        ".contents",
        ".detail",
        ".article",
        "article",
        "main",
    )
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            text = clean_text(element.get_text(" ", strip=True))
            if len(text) >= 30:
                return text

    body = soup.body or soup
    return clean_text(body.get_text(" ", strip=True))


def enrich_notice_from_detail(crawler: BaseCrawler, notice: NoticeData) -> NoticeData:
    if notice.get("deadline") and notice.get("content"):
        return notice

    url = str(notice.get("url") or "")
    if not url:
        return notice

    try:
        response = crawler.fetch_page(url)
        detail_text = extract_detail_text_from_html(response.text)
    except Exception as exc:
        crawler.logger.debug("Detail enrichment skipped for %s: %s", url, exc)
        return notice

    if detail_text and not notice.get("content"):
        notice["content"] = detail_text[:10000]
    if detail_text and not notice.get("summary"):
        notice["summary"] = detail_text[:500]
    if detail_text and not notice.get("deadline"):
        notice["deadline"] = extract_deadline_from_text(detail_text)

    return notice


def entry_value(entry: Any, key: str, default: str = "") -> str:
    if hasattr(entry, "get") and callable(entry.get):
        try:
            value = entry.get(key, default) or default
            if not value.__class__.__module__.startswith("unittest.mock"):
                return str(value)
        except Exception:
            pass

    value = getattr(entry, key, default) or default
    if value.__class__.__module__.startswith("unittest.mock"):
        return default
    return str(value)


def _notice_key(notice: NoticeData) -> str:
    url = clean_text(str(notice.get("url") or ""))
    if url:
        return url

    return "|".join(
        [
            clean_text(str(notice.get("agency", ""))),
            clean_text(str(notice.get("title", ""))),
            clean_text(str(notice.get("posted_date", ""))),
        ]
    )


def _prefer_text(candidate: Any, current: Any, title: str = "") -> str:
    candidate_text = clean_text(str(candidate or ""))
    current_text = clean_text(str(current or ""))
    if not candidate_text:
        return current_text
    if not current_text:
        return candidate_text

    candidate_has_title = bool(title and title in candidate_text)
    current_has_title = bool(title and title in current_text)
    if candidate_has_title and not current_has_title:
        return candidate_text
    if len(candidate_text) > len(current_text) * 2:
        return candidate_text

    return current_text


def _merge_notice_data(current: NoticeData, incoming: NoticeData) -> NoticeData:
    merged = dict(current)
    title = clean_text(str(merged.get("title") or incoming.get("title") or ""))

    for field in ("agency", "title", "url", "posted_date", "deadline"):
        if not merged.get(field) and incoming.get(field):
            merged[field] = incoming[field]

    merged["content"] = _prefer_text(incoming.get("content"), merged.get("content"), title)
    merged["summary"] = _prefer_text(incoming.get("summary"), merged.get("summary"), title)

    current_category = clean_text(str(merged.get("category") or ""))
    incoming_category = clean_text(str(incoming.get("category") or ""))
    if incoming_category and current_category in {"", "news", "other"}:
        merged["category"] = incoming_category

    for field in ("ai_tags", "recommended_for"):
        if not merged.get(field) and incoming.get(field):
            merged[field] = incoming[field]

    return merged


def dedupe_notices(notices: list[NoticeData]) -> list[NoticeData]:
    index_by_key: dict[str, int] = {}
    unique: list[NoticeData] = []

    for notice in notices:
        key = _notice_key(notice)
        if not key:
            continue

        if key in index_by_key:
            index = index_by_key[key]
            unique[index] = _merge_notice_data(unique[index], notice)
            continue

        index_by_key[key] = len(unique)
        unique.append(dict(notice))

    return unique


class RSSListMixin:
    rss_url: str

    def fetch_from_rss(self: BaseCrawler, rss_url: str | None = None) -> list[NoticeData]:
        feed = self.parse_rss(rss_url or self.rss_url)
        notices: list[NoticeData] = []

        for entry in getattr(feed, "entries", []):
            title = clean_text(entry_value(entry, "title"))
            url = entry_value(entry, "link")
            summary = clean_text(
                entry_value(entry, "summary") or entry_value(entry, "description")
            )
            published = (
                entry_value(entry, "published")
                or entry_value(entry, "pubDate")
                or entry_value(entry, "updated")
            )

            if not title or not url:
                continue

            notices.append(
                {
                    "agency": self.agency_code,
                    "title": title,
                    "url": url,
                    "posted_date": parse_date(published),
                    "deadline": None,
                    "category": self._categorize_notice(title, summary),  # type: ignore[attr-defined]
                    "summary": summary,
                    "content": summary,
                }
            )

        return notices


class HTMLListMixin:
    list_selectors = (
        "table tbody tr",
        ".board-list li",
        ".notice-list li",
        ".board_list tbody tr",
        ".notice-table tbody tr",
        ".list-body li",
        ".news-item",
        ".notice-item",
        "article .item",
    )
    date_selectors = (
        ".date",
        ".reg-date",
        ".regDate",
        ".date-time",
        ".board-date",
        "td.date",
        "td:nth-last-child(2)",
    )

    def fetch_from_html(self: BaseCrawler, url: str | None = None) -> list[NoticeData]:
        response = self.fetch_page(url or self.notice_url)
        soup = self.parse_html(response.text)
        return self.parse_html_list(soup)

    def build_url_from_onclick(self: BaseCrawler, onclick: str) -> str:
        return ""

    def normalize_detail_url(self: BaseCrawler, href: str) -> str:
        if href.startswith("?"):
            return urljoin(self.notice_url, href)
        return self.to_absolute_url(href)

    def parse_html_list(self: BaseCrawler, soup: BeautifulSoup) -> list[NoticeData]:
        rows: list[Tag] = []
        for selector in self.list_selectors:  # type: ignore[attr-defined]
            rows = [row for row in soup.select(selector) if isinstance(row, Tag)]
            if rows:
                break

        notices: list[NoticeData] = []
        for row in rows:
            link = row.select_one("a[href]")
            if not link:
                continue

            title = clean_text(link.get_text(" ", strip=True))
            href = clean_text(link.get("href", ""))
            if not href or href.startswith("#") or href.startswith("javascript:"):
                href = self.build_url_from_onclick(clean_text(link.get("onclick", "")))  # type: ignore[attr-defined]
            posted_date = self._extract_date(row)  # type: ignore[attr-defined]

            if not title or not href:
                continue

            notices.append(
                enrich_notice_from_detail(
                    self,
                    {
                    "agency": self.agency_code,
                    "title": title,
                    "url": self.normalize_detail_url(href),  # type: ignore[attr-defined]
                    "posted_date": posted_date,
                    "deadline": None,
                    "category": self._categorize_notice(title),  # type: ignore[attr-defined]
                    "summary": "",
                    "content": "",
                    },
                )
            )

        return notices

    def _extract_date(self: BaseCrawler, row: Tag) -> str:
        for selector in self.date_selectors:  # type: ignore[attr-defined]
            element = row.select_one(selector)
            if element:
                parsed = parse_date(element.get_text(" ", strip=True))
                if parsed:
                    return parsed

        parsed = parse_date(row.get_text(" ", strip=True))
        return parsed


def first_regex(pattern: str, text: str, default: str = "") -> str:
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else default
