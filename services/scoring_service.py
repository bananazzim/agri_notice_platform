from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Iterable, Mapping

from django.utils import timezone

from apps.notices.constants import DEADLINE_SOON_DAYS


@dataclass(frozen=True)
class RuleScoreResult:
    score: int
    reasons: tuple[str, ...]
    smartfarm_related: bool


KEYWORD_RULES: tuple[tuple[str, int, tuple[str, ...]], ...] = (
    (
        "smartfarm",
        30,
        (
            "스마트팜",
            "smart farm",
            "smartfarm",
            "스마트 농업",
            "스마트농업",
            "디지털농업",
            "digital agriculture",
        ),
    ),
    ("youth_farmer", 25, ("청년농", "청년 농", "청년창업농", "청년후계농", "청년농업인")),
    ("startup", 20, ("창업", "스타트업", "예비창업", "사업화", "입주기업", "벤처")),
    ("ai", 20, ("ai", "인공지능", "데이터", "디지털", "ict", "자동화")),
    ("contest", 15, ("경진대회", "공모전", "contest", "challenge", "챌린지", "해커톤")),
    ("rd", 15, ("r&d", "연구개발", "기술개발", "실증", "연구", "과제")),
)

CATEGORY_WEIGHTS: dict[str, int] = {
    "startup": 20,
    "contest": 15,
    "rd": 15,
    "support": 8,
    "education": 5,
}

AGENCY_WEIGHTS: tuple[tuple[str, int, tuple[str, ...]], ...] = (
    ("koat", 15, ("koat", "한국농업기술진흥원", "농업기술진흥원")),
    ("rda", 15, ("rda", "농촌진흥청")),
)


def calculate_rule_score(
    notice_data: Mapping[str, Any],
    agency: Any | None = None,
    *,
    today: date | None = None,
) -> RuleScoreResult:
    """Calculate the first-pass recommendation score without an AI API call."""
    today = today or timezone.localdate()
    text = _build_text(notice_data, agency)
    score = 0
    reasons: list[str] = []
    smartfarm_related = False

    for rule_name, weight, keywords in KEYWORD_RULES:
        if _contains_any(text, keywords):
            score += weight
            reasons.append(rule_name)
            if rule_name == "smartfarm":
                smartfarm_related = True

    category = str(notice_data.get("category") or "").strip().lower()
    category_weight = CATEGORY_WEIGHTS.get(category, 0)
    if category_weight:
        score += category_weight
        reasons.append(f"category:{category}")

    for agency_name, weight, keywords in AGENCY_WEIGHTS:
        if _contains_any(text, keywords):
            score += weight
            reasons.append(f"agency:{agency_name}")

    deadline = _coerce_date(notice_data.get("deadline"))
    if deadline is not None and 0 <= (deadline - today).days <= DEADLINE_SOON_DAYS:
        score += 10
        reasons.append("deadline_soon")

    return RuleScoreResult(
        score=_clamp_score(score),
        reasons=tuple(dict.fromkeys(reasons)),
        smartfarm_related=smartfarm_related,
    )


def should_request_ai(
    notice_data: Mapping[str, Any],
    agency: Any | None = None,
    *,
    user_opened_detail: bool = False,
    admin_requested: bool = False,
    already_analyzed: bool = False,
    today: date | None = None,
) -> bool:
    """Return whether this notice is allowed to spend an OpenAI API call."""
    if already_analyzed:
        return False

    result = calculate_rule_score(notice_data, agency, today=today)
    return result.score >= 70 and user_opened_detail


def _build_text(notice_data: Mapping[str, Any], agency: Any | None) -> str:
    agency_parts = [
        getattr(agency, "code", ""),
        getattr(agency, "name", ""),
        str(notice_data.get("agency") or ""),
    ]
    notice_parts = [
        str(notice_data.get("title") or ""),
        str(notice_data.get("category") or ""),
        _join_values(notice_data.get("ai_tags") or notice_data.get("tags") or []),
        _join_values(notice_data.get("recommended_for") or []),
    ]
    return " ".join([*agency_parts, *notice_parts]).casefold()


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword.casefold() in text for keyword in keywords)


def _join_values(values: Any) -> str:
    if isinstance(values, str):
        return values
    if isinstance(values, Iterable):
        return " ".join(str(value) for value in values)
    return ""


def _coerce_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _clamp_score(score: int) -> int:
    return max(0, min(100, score))
