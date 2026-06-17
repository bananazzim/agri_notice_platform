import pytest
from django.core import mail
from django.test import override_settings
from django.utils import timezone

from apps.notices.models import Agency, EmailNotificationLog, EmailSubscription, Notice
from services.email_notification_service import EmailNotificationService


@pytest.fixture
def agency(db):
    return Agency.objects.create(
        code="koat",
        name="한국농업기술진흥원",
        website_url="https://www.koat.or.kr",
    )


@pytest.fixture
def notice(agency):
    return Notice.objects.create(
        agency=agency,
        title="스마트팜 청년창업 교육생 모집",
        url="https://example.com/notices/1",
        content="스마트팜 분야 청년창업 교육 지원사업입니다.",
        summary="스마트팜 창업 교육",
        category="startup",
        posted_date=timezone.localdate(),
        importance_score=85,
        rule_score=85,
        ai_tags=["smart_farm", "startup"],
        recommended_for=["pre_startup"],
    )


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SITE_URL="http://testserver",
    NOTIFICATION_CONFIG={
        "email": {"enabled": True, "from_email": "alerts@example.com"},
    },
)
def test_send_keyword_alert_creates_log_and_email(notice):
    subscription = EmailSubscription.objects.create(
        email="user@example.com",
        keywords="스마트팜, 수출",
    )

    result = EmailNotificationService().send_for_notices([notice])

    assert result.matched == 1
    assert result.sent == 1
    assert len(mail.outbox) == 1
    assert "스마트팜 청년창업 교육생 모집" in mail.outbox[0].subject

    log = EmailNotificationLog.objects.get(subscription=subscription, notice=notice)
    assert log.status == EmailNotificationLog.STATUS_SENT
    assert log.matched_keywords == ["스마트팜"]


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SITE_URL="http://testserver",
    NOTIFICATION_CONFIG={
        "email": {"enabled": True, "from_email": "alerts@example.com"},
    },
)
def test_send_keyword_alert_skips_duplicate_log(notice):
    subscription = EmailSubscription.objects.create(
        email="user@example.com",
        keywords="스마트팜",
    )

    service = EmailNotificationService()
    first = service.send_for_notices([notice])
    second = service.send_for_notices([notice])

    assert first.sent == 1
    assert second.sent == 0
    assert second.skipped == 1
    assert EmailNotificationLog.objects.filter(subscription=subscription, notice=notice).count() == 1


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SITE_URL="http://testserver",
    NOTIFICATION_CONFIG={
        "email": {"enabled": False, "from_email": "alerts@example.com"},
    },
)
def test_email_disabled_skips_notices(notice):
    EmailSubscription.objects.create(
        email="user@example.com",
        keywords="스마트팜",
    )

    result = EmailNotificationService().send_for_notices([notice])

    assert result.skipped == 1
    assert len(getattr(mail, "outbox", [])) == 0
    assert EmailNotificationLog.objects.count() == 0
