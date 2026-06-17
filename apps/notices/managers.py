from __future__ import annotations

from datetime import timedelta

from django.db import models
from django.utils import timezone

from .constants import DEADLINE_SOON_DAYS, EXCLUDED_NOTICE_CATEGORIES


class NoticeQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_deleted=False).exclude(category__in=EXCLUDED_NOTICE_CATEGORIES)

    def not_expired(self):
        today = timezone.localdate()
        return self.filter(models.Q(deadline__isnull=True) | models.Q(deadline__gte=today))

    def deadline_soon(self, days: int = DEADLINE_SOON_DAYS):
        today = timezone.localdate()
        threshold = today + timedelta(days=days)
        return self.filter(deadline__gte=today, deadline__lte=threshold)

    def by_agency(self, agency_code: str):
        return self.filter(agency__code=agency_code)

    def by_category(self, category: str):
        return self.filter(category=category)

    def by_tag(self, tag: str):
        return self.filter(ai_tags__icontains=tag)

    def high_importance(self, score: int = 70):
        return self.filter(importance_score__gte=score)

    def recent(self, days: int = 30):
        since = timezone.localdate() - timedelta(days=days)
        return self.filter(posted_date__gte=since)

    def with_ai_analysis(self):
        return self.exclude(ai_summary="").filter(ai_analyzed_at__isnull=False)

    def by_recommended_for(self, target: str):
        return self.filter(recommended_for__icontains=target)

    def popular(self):
        return self.order_by("-view_count", "-posted_date")


class NoticeManager(models.Manager.from_queryset(NoticeQuerySet)):
    pass


class CrawlerLogQuerySet(models.QuerySet):
    def recent(self, days: int = 7):
        since = timezone.now() - timedelta(days=days)
        return self.filter(created_at__gte=since)

    def successful(self):
        return self.filter(status="success")

    def failed(self):
        return self.filter(status="failed")

    def partial(self):
        return self.filter(status="partial")

    def by_agency(self, agency_code: str):
        return self.filter(agency__code=agency_code)


class CrawlerLogManager(models.Manager.from_queryset(CrawlerLogQuerySet)):
    pass
