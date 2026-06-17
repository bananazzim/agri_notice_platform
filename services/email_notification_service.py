from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from apps.notices.models import EmailNotificationLog, EmailSubscription, Notice

logger = logging.getLogger("scheduler")


@dataclass(frozen=True)
class EmailNotificationResult:
    matched: int = 0
    sent: int = 0
    failed: int = 0
    skipped: int = 0


class EmailNotificationService:
    """Send keyword-based email alerts for newly saved notices."""

    def send_for_notices(self, notices: Iterable[Notice]) -> EmailNotificationResult:
        notice_list = list(notices)
        if not notice_list:
            return EmailNotificationResult()

        if not self._email_enabled():
            logger.info("Email notifications skipped: EMAIL_ENABLED is false.")
            return EmailNotificationResult(skipped=len(notice_list))

        base_url = self._base_url()
        if not base_url:
            logger.warning("Email notifications skipped: SITE_URL is not configured.")
            return EmailNotificationResult(skipped=len(notice_list))

        matched = sent = failed = skipped = 0
        subscriptions = (
            EmailSubscription.objects.filter(is_active=True)
            .prefetch_related("agencies")
            .order_by("created_at")
        )

        for notice in notice_list:
            notice = Notice.objects.select_related("agency").get(pk=notice.pk)
            for subscription in subscriptions:
                matched_keywords = self._matched_keywords(subscription, notice)
                if not matched_keywords:
                    continue

                matched += 1
                log = self._create_log(subscription, notice, matched_keywords)
                if log is None:
                    skipped += 1
                    continue

                try:
                    self._send_email(subscription, notice, matched_keywords, base_url)
                except Exception as exc:
                    failed += 1
                    log.status = EmailNotificationLog.STATUS_FAILED
                    log.error_message = str(exc)
                    log.save(update_fields=["status", "error_message"])
                    logger.warning(
                        "Email notification failed subscription=%s notice=%s error=%s",
                        subscription.pk,
                        notice.pk,
                        exc,
                    )
                    continue

                sent += 1
                now = timezone.now()
                log.status = EmailNotificationLog.STATUS_SENT
                log.sent_at = now
                log.save(update_fields=["status", "sent_at"])
                subscription.last_sent_at = now
                subscription.save(update_fields=["last_sent_at", "updated_at"])

        result = EmailNotificationResult(
            matched=matched,
            sent=sent,
            failed=failed,
            skipped=skipped,
        )
        logger.info("Email notification result: %s", result)
        return result

    def _email_enabled(self) -> bool:
        return bool(getattr(settings, "NOTIFICATION_CONFIG", {}).get("email", {}).get("enabled"))

    def _base_url(self) -> str:
        return str(getattr(settings, "SITE_URL", "")).rstrip("/")

    def _matched_keywords(self, subscription: EmailSubscription, notice: Notice) -> list[str]:
        if not self._agency_matches(subscription, notice):
            return []
        if subscription.categories and notice.category not in subscription.categories:
            return []

        haystack = " ".join(
            [
                notice.title or "",
                notice.summary or "",
                notice.content[:1500] if notice.content else "",
                notice.ai_summary or "",
                notice.agency.name or "",
                notice.category or "",
                " ".join(str(tag) for tag in (notice.ai_tags or [])),
            ]
        ).lower()

        return [keyword for keyword in subscription.keyword_list if keyword in haystack]

    def _agency_matches(self, subscription: EmailSubscription, notice: Notice) -> bool:
        agency_ids = {agency.pk for agency in subscription.agencies.all()}
        return not agency_ids or notice.agency_id in agency_ids

    def _create_log(
        self,
        subscription: EmailSubscription,
        notice: Notice,
        matched_keywords: list[str],
    ) -> EmailNotificationLog | None:
        try:
            with transaction.atomic():
                return EmailNotificationLog.objects.create(
                    subscription=subscription,
                    notice=notice,
                    matched_keywords=matched_keywords,
                    status=EmailNotificationLog.STATUS_PENDING,
                )
        except IntegrityError:
            return None

    def _send_email(
        self,
        subscription: EmailSubscription,
        notice: Notice,
        matched_keywords: list[str],
        base_url: str,
    ) -> None:
        notice_url = f"{base_url}{reverse('notices:notice_detail', kwargs={'pk': notice.pk})}"
        subject = f"[Agri Notice] {notice.title[:80]}"
        context = {
            "subscription": subscription,
            "notice": notice,
            "matched_keywords": matched_keywords,
            "notice_url": notice_url,
        }
        text_body = render_to_string("emails/notice_alert.txt", context)
        html_body = render_to_string("emails/notice_alert.html", context)
        from_email = getattr(settings, "NOTIFICATION_CONFIG", {}).get("email", {}).get(
            "from_email",
            getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"),
        )

        send_mail(
            subject=subject,
            message=text_body,
            from_email=from_email,
            recipient_list=[subscription.email],
            html_message=html_body,
            fail_silently=False,
        )
