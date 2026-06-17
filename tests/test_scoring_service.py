from datetime import date
from types import SimpleNamespace

from services.scoring_service import calculate_rule_score, should_request_ai


def test_calculate_rule_score_caps_high_value_smartfarm_notice():
    agency = SimpleNamespace(code="koat", name="한국농업기술진흥원")
    result = calculate_rule_score(
        {
            "title": "스마트팜 청년농 AI 창업 경진대회 모집",
            "category": "startup",
            "deadline": date(2026, 6, 20),
            "ai_tags": ["smart_farm", "startup"],
        },
        agency,
        today=date(2026, 6, 17),
    )

    assert result.score == 100
    assert result.smartfarm_related is True
    assert "smartfarm" in result.reasons
    assert "deadline_soon" in result.reasons


def test_calculate_rule_score_keeps_generic_support_notice_low():
    result = calculate_rule_score(
        {
            "title": "일반 지원사업 안내",
            "category": "support",
            "deadline": None,
        },
        today=date(2026, 6, 17),
    )

    assert result.score == 8
    assert result.smartfarm_related is False


def test_should_request_ai_requires_detail_view_for_regular_flow():
    agency = SimpleNamespace(code="koat", name="한국농업기술진흥원")
    notice_data = {
        "title": "스마트팜 청년농 AI 창업 경진대회 모집",
        "category": "startup",
        "deadline": date(2026, 6, 20),
    }

    assert should_request_ai(
        notice_data,
        agency,
        user_opened_detail=False,
        today=date(2026, 6, 17),
    ) is False
    assert should_request_ai(
        notice_data,
        agency,
        user_opened_detail=True,
        today=date(2026, 6, 17),
    ) is True


def test_should_request_ai_allows_high_score_clicked_notice_without_smartfarm_keyword():
    notice_data = {
        "title": "이화여대 E-LIFETHON AI 창업 해커톤",
        "category": "startup",
        "deadline": date(2026, 6, 22),
    }

    assert should_request_ai(
        notice_data,
        user_opened_detail=True,
        today=date(2026, 6, 17),
    ) is True


def test_should_request_ai_respects_click_and_cache_rules():
    low_value_notice = {
        "title": "일반 공지",
        "category": "other",
        "deadline": None,
    }
    high_value_notice = {
        "title": "스마트팜 청년농 AI 창업 경진대회 모집",
        "category": "startup",
        "deadline": date(2026, 6, 20),
    }
    agency = SimpleNamespace(code="koat", name="한국농업기술진흥원")

    assert should_request_ai(low_value_notice, admin_requested=True) is False
    assert should_request_ai(
        high_value_notice,
        agency,
        admin_requested=True,
        user_opened_detail=False,
        today=date(2026, 6, 17),
    ) is False
    assert should_request_ai(
        high_value_notice,
        agency,
        user_opened_detail=True,
        today=date(2026, 6, 17),
    ) is True
    assert should_request_ai(
        high_value_notice,
        agency,
        user_opened_detail=True,
        already_analyzed=True,
        today=date(2026, 6, 17),
    ) is False
