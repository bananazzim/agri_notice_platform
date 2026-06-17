# Generated for agri_notice_platform Step 2.

import uuid

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Agency",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=50, unique=True)),
                ("name", models.CharField(max_length=255, unique=True)),
                ("name_en", models.CharField(blank=True, max_length=255)),
                ("description", models.TextField(blank=True)),
                ("website_url", models.URLField()),
                ("notice_url", models.URLField(blank=True)),
                ("api_url", models.URLField(blank=True)),
                ("rss_url", models.URLField(blank=True)),
                ("crawler_priority", models.PositiveSmallIntegerField(default=100)),
                (
                    "crawler_method",
                    models.CharField(
                        choices=[
                            ("api", "Open API"),
                            ("rss", "RSS Feed"),
                            ("html", "HTML Crawling"),
                            ("playwright", "Playwright"),
                        ],
                        default="html",
                        max_length=20,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("total_notices", models.PositiveIntegerField(default=0)),
                ("last_crawl_at", models.DateTimeField(blank=True, null=True)),
                (
                    "last_crawl_status",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("success", "Success"),
                            ("failed", "Failed"),
                            ("partial", "Partial"),
                        ],
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["crawler_priority", "code"],
            },
        ),
        migrations.CreateModel(
            name="Notice",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(db_index=True, max_length=500)),
                ("url", models.URLField(max_length=1000, unique=True)),
                ("content", models.TextField(blank=True)),
                ("summary", models.TextField(blank=True)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("support", "Support Program"),
                            ("education", "Education"),
                            ("contest", "Contest"),
                            ("startup", "Startup"),
                            ("rd", "R&D"),
                            ("job", "Job"),
                            ("news", "News"),
                            ("other", "Other"),
                        ],
                        db_index=True,
                        default="other",
                        max_length=30,
                    ),
                ),
                ("posted_date", models.DateField(db_index=True)),
                ("deadline", models.DateField(blank=True, db_index=True, null=True)),
                ("is_deadline_soon", models.BooleanField(db_index=True, default=False)),
                ("ai_summary", models.TextField(blank=True)),
                ("ai_tags", models.JSONField(blank=True, default=list)),
                (
                    "importance_score",
                    models.PositiveSmallIntegerField(
                        db_index=True,
                        default=50,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(100),
                        ],
                    ),
                ),
                ("recommended_for", models.JSONField(blank=True, default=list)),
                ("ai_analyzed_at", models.DateTimeField(blank=True, null=True)),
                ("view_count", models.PositiveIntegerField(default=0)),
                ("bookmark_count", models.PositiveIntegerField(default=0)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "agency",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="notices",
                        to="notices.agency",
                    ),
                ),
            ],
            options={
                "ordering": ["-posted_date", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="CrawlerLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("success", "Success"),
                            ("failed", "Failed"),
                            ("partial", "Partial"),
                        ],
                        max_length=20,
                    ),
                ),
                ("notices_collected", models.PositiveIntegerField(default=0)),
                ("notices_saved", models.PositiveIntegerField(default=0)),
                ("notices_duplicated", models.PositiveIntegerField(default=0)),
                ("notices_failed", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("error_traceback", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "agency",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="crawler_logs",
                        to="notices.agency",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="CrawlerStatus",
            fields=[
                ("total_crawls", models.PositiveIntegerField(default=0)),
                ("successful_crawls", models.PositiveIntegerField(default=0)),
                ("failed_crawls", models.PositiveIntegerField(default=0)),
                ("partial_crawls", models.PositiveIntegerField(default=0)),
                ("total_notices_collected", models.PositiveIntegerField(default=0)),
                ("total_notices_saved", models.PositiveIntegerField(default=0)),
                ("average_crawl_time", models.FloatField(default=0.0)),
                (
                    "last_status",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("success", "Success"),
                            ("failed", "Failed"),
                            ("partial", "Partial"),
                        ],
                        max_length=20,
                    ),
                ),
                ("last_error_message", models.TextField(blank=True)),
                ("last_crawled_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "agency",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="crawler_status",
                        serialize=False,
                        to="notices.agency",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Crawler statuses",
            },
        ),
        migrations.CreateModel(
            name="Favorite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "notice",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="favorites",
                        to="notices.notice",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notice_favorites",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="WatchAgency",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "agency",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="watchers",
                        to="notices.agency",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="watch_agencies",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="WatchTag",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tag", models.CharField(max_length=80)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="watch_tags",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="agency",
            index=models.Index(fields=["code"], name="agency_code_idx"),
        ),
        migrations.AddIndex(
            model_name="agency",
            index=models.Index(fields=["is_active", "crawler_priority"], name="agency_active_priority_idx"),
        ),
        migrations.AddIndex(
            model_name="notice",
            index=models.Index(fields=["agency", "-posted_date"], name="notice_agency_posted_idx"),
        ),
        migrations.AddIndex(
            model_name="notice",
            index=models.Index(fields=["category", "-posted_date"], name="notice_category_posted_idx"),
        ),
        migrations.AddIndex(
            model_name="notice",
            index=models.Index(fields=["deadline", "is_deadline_soon"], name="notice_deadline_idx"),
        ),
        migrations.AddIndex(
            model_name="notice",
            index=models.Index(fields=["importance_score", "-posted_date"], name="notice_importance_idx"),
        ),
        migrations.AddIndex(
            model_name="notice",
            index=models.Index(fields=["is_deleted", "-posted_date"], name="notice_active_posted_idx"),
        ),
        migrations.AddIndex(
            model_name="notice",
            index=models.Index(fields=["agency", "title", "posted_date"], name="notice_natural_key_idx"),
        ),
        migrations.AddConstraint(
            model_name="notice",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_deleted", False)),
                fields=("agency", "title", "posted_date"),
                name="uniq_active_notice_agency_title_date",
            ),
        ),
        migrations.AddIndex(
            model_name="crawlerlog",
            index=models.Index(fields=["agency", "-created_at"], name="crawler_log_agency_created_idx"),
        ),
        migrations.AddIndex(
            model_name="crawlerlog",
            index=models.Index(fields=["status", "-created_at"], name="crawler_log_status_created_idx"),
        ),
        migrations.AddConstraint(
            model_name="favorite",
            constraint=models.UniqueConstraint(fields=("user", "notice"), name="uniq_user_notice_favorite"),
        ),
        migrations.AddIndex(
            model_name="favorite",
            index=models.Index(fields=["user", "-created_at"], name="favorite_user_created_idx"),
        ),
        migrations.AddConstraint(
            model_name="watchtag",
            constraint=models.UniqueConstraint(fields=("user", "tag"), name="uniq_user_watch_tag"),
        ),
        migrations.AddIndex(
            model_name="watchtag",
            index=models.Index(fields=["user", "is_active"], name="watch_tag_user_active_idx"),
        ),
        migrations.AddConstraint(
            model_name="watchagency",
            constraint=models.UniqueConstraint(fields=("user", "agency"), name="uniq_user_watch_agency"),
        ),
        migrations.AddIndex(
            model_name="watchagency",
            index=models.Index(fields=["user", "is_active"], name="watch_agency_user_active_idx"),
        ),
    ]
