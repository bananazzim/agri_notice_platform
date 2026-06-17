from __future__ import annotations

import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .constants import (
    CRAWLER_METHOD_CHOICES,
    CRAWLER_STATUS_CHOICES,
    DEADLINE_SOON_DAYS,
    IMPORTANCE_SCORE_DEFAULT,
    IMPORTANCE_SCORE_MAX,
    IMPORTANCE_SCORE_MIN,
    NOTICE_CATEGORIES,
    AI_ANALYSIS_STATUS_CHOICES,
    SCORE_SOURCE_CHOICES,
)
from .managers import CrawlerLogManager, NoticeManager


class Agency(models.Model):
    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=255, unique=True)
    name_en = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    website_url = models.URLField()
    notice_url = models.URLField(blank=True)
    api_url = models.URLField(blank=True)
    rss_url = models.URLField(blank=True)

    crawler_priority = models.PositiveSmallIntegerField(default=100)
    crawler_method = models.CharField(
        max_length=20,
        choices=CRAWLER_METHOD_CHOICES,
        default="html",
    )
    is_active = models.BooleanField(default=True)

    total_notices = models.PositiveIntegerField(default=0)
    last_crawl_at = models.DateTimeField(null=True, blank=True)
    last_crawl_status = models.CharField(
        max_length=20,
        choices=CRAWLER_STATUS_CHOICES,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["crawler_priority", "code"]
        indexes = [
            models.Index(fields=["code"], name="agency_code_idx"),
            models.Index(fields=["is_active", "crawler_priority"], name="agency_active_priority_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class Notice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.PROTECT, related_name="notices")

    title = models.CharField(max_length=500, db_index=True)
    url = models.URLField(max_length=1000, unique=True)
    content = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    category = models.CharField(
        max_length=30,
        choices=NOTICE_CATEGORIES,
        default="other",
        db_index=True,
    )

    posted_date = models.DateField(db_index=True)
    deadline = models.DateField(null=True, blank=True, db_index=True)
    is_deadline_soon = models.BooleanField(default=False, db_index=True)

    ai_summary = models.TextField(blank=True)
    ai_tags = models.JSONField(default=list, blank=True)
    rule_score = models.PositiveSmallIntegerField(
        default=0,
        validators=[
            MinValueValidator(IMPORTANCE_SCORE_MIN),
            MaxValueValidator(IMPORTANCE_SCORE_MAX),
        ],
        db_index=True,
    )
    importance_score = models.PositiveSmallIntegerField(
        default=IMPORTANCE_SCORE_DEFAULT,
        validators=[
            MinValueValidator(IMPORTANCE_SCORE_MIN),
            MaxValueValidator(IMPORTANCE_SCORE_MAX),
        ],
        db_index=True,
    )
    score_source = models.CharField(
        max_length=20,
        choices=SCORE_SOURCE_CHOICES,
        default="rule",
        db_index=True,
    )
    recommended_for = models.JSONField(default=list, blank=True)
    ai_analysis_status = models.CharField(
        max_length=20,
        choices=AI_ANALYSIS_STATUS_CHOICES,
        default="pending",
        db_index=True,
    )
    ai_analysis_error = models.TextField(blank=True)
    ai_analyzed_at = models.DateTimeField(null=True, blank=True)

    view_count = models.PositiveIntegerField(default=0)
    bookmark_count = models.PositiveIntegerField(default=0)
    is_deleted = models.BooleanField(default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = NoticeManager()

    class Meta:
        ordering = ["-posted_date", "-created_at"]
        indexes = [
            models.Index(fields=["agency", "-posted_date"], name="notice_agency_posted_idx"),
            models.Index(fields=["category", "-posted_date"], name="notice_category_posted_idx"),
            models.Index(fields=["deadline", "is_deadline_soon"], name="notice_deadline_idx"),
            models.Index(fields=["rule_score", "-posted_date"], name="notice_rule_score_idx"),
            models.Index(fields=["importance_score", "-posted_date"], name="notice_importance_idx"),
            models.Index(fields=["ai_analysis_status", "-posted_date"], name="notice_ai_status_idx"),
            models.Index(fields=["is_deleted", "-posted_date"], name="notice_active_posted_idx"),
            models.Index(fields=["agency", "title", "posted_date"], name="notice_natural_key_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["agency", "title", "posted_date"],
                condition=Q(is_deleted=False),
                name="uniq_active_notice_agency_title_date",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.agency.code}] {self.title[:80]}"

    def save(self, *args, **kwargs):
        self.update_deadline_soon_flag()
        super().save(*args, **kwargs)

    @property
    def summary_raw(self) -> str:
        return self.summary

    @summary_raw.setter
    def summary_raw(self, value: str) -> None:
        self.summary = value

    @property
    def days_to_deadline(self) -> int | None:
        if self.deadline is None:
            return None
        return (self.deadline - timezone.localdate()).days

    @property
    def is_expired(self) -> bool:
        return self.deadline is not None and self.deadline < timezone.localdate()

    def update_deadline_soon_flag(self) -> None:
        if self.deadline is None:
            self.is_deadline_soon = False
            return

        days_left = (self.deadline - timezone.localdate()).days
        self.is_deadline_soon = 0 <= days_left <= DEADLINE_SOON_DAYS


class CrawlerLog(models.Model):
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="crawler_logs")
    status = models.CharField(max_length=20, choices=CRAWLER_STATUS_CHOICES)

    notices_collected = models.PositiveIntegerField(default=0)
    notices_saved = models.PositiveIntegerField(default=0)
    notices_duplicated = models.PositiveIntegerField(default=0)
    notices_failed = models.PositiveIntegerField(default=0)

    error_message = models.TextField(blank=True)
    error_traceback = models.TextField(blank=True)

    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = CrawlerLogManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agency", "-created_at"], name="crawler_log_agency_created_idx"),
            models.Index(fields=["status", "-created_at"], name="crawler_log_status_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.agency.code} {self.status} {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def start_time(self):
        return self.started_at

    @start_time.setter
    def start_time(self, value):
        self.started_at = value

    @property
    def end_time(self):
        return self.finished_at or self.started_at

    @end_time.setter
    def end_time(self, value):
        self.finished_at = value

    @property
    def duration_seconds(self) -> float:
        if self.finished_at is None:
            return 0.0
        return (self.finished_at - self.started_at).total_seconds()

    @property
    def duration_minutes(self) -> float:
        return round(self.duration_seconds / 60, 2)

    @property
    def success_rate(self) -> float:
        if self.notices_collected == 0:
            return 0.0
        return round((self.notices_saved / self.notices_collected) * 100, 2)


class CrawlerStatus(models.Model):
    agency = models.OneToOneField(
        Agency,
        on_delete=models.CASCADE,
        related_name="crawler_status",
        primary_key=True,
    )

    total_crawls = models.PositiveIntegerField(default=0)
    successful_crawls = models.PositiveIntegerField(default=0)
    failed_crawls = models.PositiveIntegerField(default=0)
    partial_crawls = models.PositiveIntegerField(default=0)

    total_notices_collected = models.PositiveIntegerField(default=0)
    total_notices_saved = models.PositiveIntegerField(default=0)
    average_crawl_time = models.FloatField(default=0.0)

    last_status = models.CharField(max_length=20, choices=CRAWLER_STATUS_CHOICES, blank=True)
    last_error_message = models.TextField(blank=True)
    last_crawled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Crawler statuses"

    def __str__(self) -> str:
        return f"{self.agency.code} crawler status"

    @property
    def success_rate(self) -> float:
        if self.total_crawls == 0:
            return 0.0
        return round((self.successful_crawls / self.total_crawls) * 100, 2)

    @property
    def average_save_rate(self) -> float:
        if self.total_notices_collected == 0:
            return 0.0
        return round((self.total_notices_saved / self.total_notices_collected) * 100, 2)


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notice_favorites")
    notice = models.ForeignKey(Notice, on_delete=models.CASCADE, related_name="favorites")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "notice"], name="uniq_user_notice_favorite"),
        ]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="favorite_user_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} -> {self.notice_id}"


class WatchTag(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watch_tags")
    tag = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "tag"], name="uniq_user_watch_tag"),
        ]
        indexes = [
            models.Index(fields=["user", "is_active"], name="watch_tag_user_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}: {self.tag}"


class WatchAgency(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watch_agencies")
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="watchers")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "agency"], name="uniq_user_watch_agency"),
        ]
        indexes = [
            models.Index(fields=["user", "is_active"], name="watch_agency_user_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}: {self.agency.code}"
