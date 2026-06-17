from __future__ import annotations

import pytest
from django.utils import timezone

from ai.analyzer import NoticeAnalysisResult
from apps.notices.models import Agency, Notice
from core.exceptions import AIAnalysisError
from services.ai_service import NoticeAIService


class FakeAnalyzer:
    def __init__(self, *, raises: bool = False):
        self.raises = raises
        self.calls: list[dict[str, str]] = []

    def analyze_notice_data(self, notice_data):
        self.calls.append(notice_data)
        if self.raises:
            raise AIAnalysisError("quota exceeded")
        return NoticeAnalysisResult(
            summary="1. 핵심 지원 내용\n2. 스마트팜 창업에 유용\n3. 신청 조건 확인 필요",
            tags=["smart_farm", "startup"],
            importance_score=88,
            recommended_for=["student", "pre_startup"],
            provider="openai",
        )


@pytest.fixture
def agency():
    return Agency.objects.create(
        code="koat",
        name="한국농업기술진흥원",
        website_url="https://www.koat.or.kr",
    )


@pytest.fixture
def high_value_notice(agency):
    return Notice.objects.create(
        agency=agency,
        title="스마트팜 청년농 AI 창업 경진대회 모집",
        url="https://example.com/high",
        content="본문" * 800,
        category="startup",
        posted_date=timezone.localdate(),
        rule_score=100,
        importance_score=100,
        score_source="rule",
        ai_analysis_status="pending",
    )


@pytest.mark.django_db
def test_analyze_notice_saves_openai_result_for_detail_view(high_value_notice):
    analyzer = FakeAnalyzer()
    service = NoticeAIService(analyzer=analyzer)

    outcome = service.analyze_notice(high_value_notice, user_opened_detail=True)

    high_value_notice.refresh_from_db()
    assert outcome.analyzed is True
    assert high_value_notice.ai_analysis_status == "success"
    assert high_value_notice.score_source == "ai"
    assert high_value_notice.importance_score == 88
    assert high_value_notice.ai_tags == ["smart_farm", "startup"]
    assert high_value_notice.recommended_for == ["student", "pre_startup"]
    assert high_value_notice.ai_analyzed_at is not None
    assert len(analyzer.calls) == 1
    assert len(analyzer.calls[0]["content"]) == 1000


@pytest.mark.django_db
def test_analyze_notice_skips_low_value_notice(agency):
    notice = Notice.objects.create(
        agency=agency,
        title="일반 지원사업 안내",
        url="https://example.com/low",
        content="일반 본문",
        category="support",
        posted_date=timezone.localdate(),
        rule_score=8,
        importance_score=8,
        score_source="rule",
    )
    analyzer = FakeAnalyzer()
    service = NoticeAIService(analyzer=analyzer)

    outcome = service.analyze_notice(notice, user_opened_detail=True)

    notice.refresh_from_db()
    assert outcome.skipped is True
    assert outcome.reason == "not_eligible"
    assert notice.ai_analysis_status == "skipped"
    assert analyzer.calls == []


@pytest.mark.django_db
def test_analyze_notice_reuses_existing_ai_result(high_value_notice):
    high_value_notice.ai_summary = "existing"
    high_value_notice.ai_analyzed_at = timezone.now()
    high_value_notice.ai_analysis_status = "success"
    high_value_notice.save()
    analyzer = FakeAnalyzer()
    service = NoticeAIService(analyzer=analyzer)

    outcome = service.analyze_notice(high_value_notice, user_opened_detail=True)

    assert outcome.skipped is True
    assert outcome.reason == "already_analyzed"
    assert analyzer.calls == []


@pytest.mark.django_db
def test_analyze_notice_failure_keeps_rule_based_score(high_value_notice):
    analyzer = FakeAnalyzer(raises=True)
    service = NoticeAIService(analyzer=analyzer)

    outcome = service.analyze_notice(high_value_notice, user_opened_detail=True)

    high_value_notice.refresh_from_db()
    assert outcome.reason == "failed"
    assert high_value_notice.ai_analysis_status == "failed"
    assert high_value_notice.importance_score == high_value_notice.rule_score
    assert high_value_notice.score_source == "rule"
    assert "quota exceeded" in high_value_notice.ai_analysis_error


@pytest.mark.django_db
def test_analyze_queryset_does_not_call_openai_without_detail_click(high_value_notice):
    analyzer = FakeAnalyzer()
    service = NoticeAIService(analyzer=analyzer)

    outcomes = service.analyze_queryset(
        Notice.objects.filter(pk=high_value_notice.pk),
        admin_requested=True,
        force=True,
    )

    high_value_notice.refresh_from_db()
    assert outcomes[0].skipped is True
    assert outcomes[0].reason == "not_eligible"
    assert high_value_notice.ai_analysis_status == "skipped"
    assert analyzer.calls == []
