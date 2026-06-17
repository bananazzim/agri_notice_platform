from __future__ import annotations

from dataclasses import dataclass

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.notices.models import Agency, Notice
from apps.notices.views import get_notice_queryset


@dataclass(frozen=True)
class FakeOutcome:
    analyzed: bool = False
    skipped: bool = True
    reason: str = "test"
    provider: str = ""


class FakeAIService:
    calls: list[dict[str, object]] = []

    def analyze_notice(self, notice, *, user_opened_detail=False, admin_requested=False, force=False):
        self.calls.append(
            {
                "notice_id": notice.pk,
                "user_opened_detail": user_opened_detail,
                "admin_requested": admin_requested,
                "force": force,
            }
        )
        return FakeOutcome()


@pytest.fixture
def agency():
    return Agency.objects.create(
        code="koat",
        name="한국농업기술진흥원",
        website_url="https://www.koat.or.kr",
    )


@pytest.fixture
def notice(agency):
    return Notice.objects.create(
        agency=agency,
        title="스마트팜 청년농 AI 창업 경진대회 모집",
        url="https://example.com/notice",
        content="본문",
        category="startup",
        posted_date=timezone.localdate(),
        rule_score=100,
        importance_score=100,
        ai_analysis_status="pending",
    )


@pytest.mark.django_db
def test_notice_detail_view_triggers_ai_service(client, monkeypatch, notice):
    FakeAIService.calls = []
    monkeypatch.setattr("apps.notices.views.NoticeAIService", FakeAIService)

    response = client.get(reverse("notices:notice_detail", args=[notice.pk]))

    assert response.status_code == 200
    assert FakeAIService.calls == [
        {
            "notice_id": notice.pk,
            "user_opened_detail": True,
            "admin_requested": False,
            "force": False,
        }
    ]
    assert response.context["ai_outcome"].reason == "test"


@pytest.mark.django_db
def test_notice_api_detail_does_not_trigger_ai_service(client, monkeypatch, notice):
    FakeAIService.calls = []
    monkeypatch.setattr("apps.notices.views.NoticeAIService", FakeAIService)

    response = client.get(reverse("notices:api_notice_detail", args=[notice.pk]))

    assert response.status_code == 200
    assert FakeAIService.calls == []


@pytest.mark.django_db
def test_notice_queryset_supports_importance_ordering(agency):
    low = Notice.objects.create(
        agency=agency,
        title="일반 지원사업",
        url="https://example.com/low",
        category="support",
        posted_date=timezone.localdate(),
        importance_score=8,
    )
    high = Notice.objects.create(
        agency=agency,
        title="스마트팜 창업 지원사업",
        url="https://example.com/high",
        category="startup",
        posted_date=timezone.localdate(),
        importance_score=95,
    )

    notices = list(get_notice_queryset({"ordering": "importance"}))

    assert notices[:2] == [high, low]
