from __future__ import annotations

from django.contrib import admin, messages
from django.core.management import call_command
from django.utils.html import format_html

from services.ai_service import NoticeAIService

from .models import (
    Agency,
    CrawlerLog,
    CrawlerStatus,
    EmailNotificationLog,
    EmailSubscription,
    Favorite,
    Notice,
    WatchAgency,
    WatchTag,
)


admin.site.site_header = "Agri Notice Admin"
admin.site.site_title = "Agri Notice"
admin.site.index_title = "Operations"


STATUS_COLORS = {
    "pending": "#6b7280",
    "running": "#2563eb",
    "success": "#18794e",
    "failed": "#b42318",
    "partial": "#a05a00",
}


def render_badge(label: str, color: str = "#6b7280") -> str:
    return format_html(
        '<span style="display:inline-block; min-width:64px; text-align:center; '
        'background:{}; color:#fff; padding:3px 8px; border-radius:999px; '
        'font-size:12px; font-weight:600;">{}</span>',
        color,
        label or "-",
    )


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "crawler_method",
        "is_active",
        "crawler_priority",
        "total_notices",
        "last_crawl_status_badge",
        "last_crawl_at",
    )
    list_filter = ("is_active", "crawler_method", "last_crawl_status")
    search_fields = ("code", "name", "name_en", "description")
    ordering = ("crawler_priority", "code")
    actions = ("run_selected_crawlers", "activate_agencies", "deactivate_agencies")
    readonly_fields = ("total_notices", "last_crawl_at", "last_crawl_status", "created_at", "updated_at")

    fieldsets = (
        ("Basic", {"fields": ("code", "name", "name_en", "description")}),
        ("Source", {"fields": ("website_url", "notice_url", "api_url", "rss_url")}),
        ("Crawler", {"fields": ("crawler_method", "crawler_priority", "is_active")}),
        (
            "Status",
            {
                "fields": ("total_notices", "last_crawl_status", "last_crawl_at", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Status")
    def last_crawl_status_badge(self, obj: Agency):
        return render_badge(obj.last_crawl_status or "never", STATUS_COLORS.get(obj.last_crawl_status, "#6b7280"))

    @admin.action(description="Run crawler for selected agencies")
    def run_selected_crawlers(self, request, queryset):
        success_count = 0
        for agency in queryset:
            try:
                call_command("run_crawler", agency=agency.code)
                success_count += 1
            except Exception as exc:
                self.message_user(
                    request,
                    f"{agency.code} crawler failed: {exc}",
                    level=messages.ERROR,
                )

        if success_count:
            self.message_user(request, f"Started crawler for {success_count} agencies.", level=messages.SUCCESS)

    @admin.action(description="Activate selected agencies")
    def activate_agencies(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"Activated {count} agencies.", level=messages.SUCCESS)

    @admin.action(description="Deactivate selected agencies")
    def deactivate_agencies(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {count} agencies.", level=messages.WARNING)


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = (
        "title_short",
        "agency",
        "category",
        "posted_date",
        "deadline_badge",
        "ai_status",
    )
    list_filter = (
        "category",
        "is_deadline_soon",
        "is_deleted",
        "agency",
        "posted_date",
        "deadline",
        "ai_analyzed_at",
    )
    search_fields = ("title", "content", "summary", "ai_summary", "agency__name", "agency__code", "url")
    date_hierarchy = "posted_date"
    ordering = ("-posted_date", "-created_at")
    list_select_related = ("agency",)
    actions = ("reanalyze_selected_notices", "mark_deleted", "restore_notices")
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "ai_analyzed_at",
        "bookmark_count",
        "days_to_deadline_display",
        "source_link",
    )

    fieldsets = (
        ("Basic", {"fields": ("id", "agency", "title", "url", "source_link", "category")}),
        ("Content", {"fields": ("summary", "content")}),
        ("Dates", {"fields": ("posted_date", "deadline", "is_deadline_soon", "days_to_deadline_display")}),
        (
            "AI Analysis",
            {
                "fields": ("ai_summary", "ai_tags", "recommended_for", "ai_analyzed_at"),
            },
        ),
        ("Engagement", {"fields": ("bookmark_count", "is_deleted"), "classes": ("collapse",)}),
        ("Metadata", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Title", ordering="title")
    def title_short(self, obj: Notice):
        return obj.title[:80] + ("..." if len(obj.title) > 80 else "")

    @admin.display(description="Deadline", ordering="deadline")
    def deadline_badge(self, obj: Notice):
        if obj.deadline is None:
            return render_badge("none", "#6b7280")
        if obj.is_expired:
            return render_badge(obj.deadline.strftime("%Y-%m-%d"), "#b42318")
        if obj.is_deadline_soon:
            return render_badge(obj.deadline.strftime("%Y-%m-%d"), "#a05a00")
        return render_badge(obj.deadline.strftime("%Y-%m-%d"), "#18794e")

    @admin.display(description="AI", ordering="ai_analyzed_at")
    def ai_status(self, obj: Notice):
        return render_badge("done", "#18794e") if obj.ai_analyzed_at else render_badge("pending", "#6b7280")

    @admin.display(description="Days left")
    def days_to_deadline_display(self, obj: Notice):
        if obj.days_to_deadline is None:
            return "-"
        if obj.days_to_deadline == 0:
            return "today"
        return obj.days_to_deadline

    @admin.display(description="Source")
    def source_link(self, obj: Notice):
        if not obj.url:
            return "-"
        return format_html('<a href="{}" target="_blank" rel="noopener">Open source</a>', obj.url)

    @admin.action(description="Re-run AI analysis for selected notices")
    def reanalyze_selected_notices(self, request, queryset):
        service = NoticeAIService()
        success_count = 0
        for notice in queryset.select_related("agency"):
            try:
                outcome = service.analyze_notice(
                    notice,
                    admin_requested=True,
                    force=True,
                )
                if outcome.analyzed:
                    success_count += 1
                elif outcome.reason == "failed":
                    self.message_user(
                        request,
                        f"AI analysis failed for {notice.pk}: {notice.ai_analysis_error}",
                        level=messages.ERROR,
                    )
            except Exception as exc:
                self.message_user(
                    request,
                    f"AI analysis failed for {notice.pk}: {exc}",
                    level=messages.ERROR,
                )

        self.message_user(request, f"Analyzed {success_count} notices.", level=messages.SUCCESS)

    @admin.action(description="Soft delete selected notices")
    def mark_deleted(self, request, queryset):
        count = queryset.update(is_deleted=True)
        self.message_user(request, f"Soft deleted {count} notices.", level=messages.WARNING)

    @admin.action(description="Restore selected notices")
    def restore_notices(self, request, queryset):
        count = queryset.update(is_deleted=False)
        self.message_user(request, f"Restored {count} notices.", level=messages.SUCCESS)


@admin.register(CrawlerLog)
class CrawlerLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "agency",
        "status_badge",
        "notices_collected",
        "notices_saved",
        "notices_duplicated",
        "notices_failed",
        "duration_display",
    )
    list_filter = ("status", "agency", "created_at")
    search_fields = ("agency__name", "agency__code", "error_message", "error_traceback")
    ordering = ("-created_at",)
    list_select_related = ("agency",)
    readonly_fields = (
        "agency",
        "status",
        "notices_collected",
        "notices_saved",
        "notices_duplicated",
        "notices_failed",
        "error_message",
        "error_traceback",
        "started_at",
        "finished_at",
        "created_at",
        "duration_display",
        "success_rate_display",
    )

    fieldsets = (
        ("Run", {"fields": ("agency", "status", "created_at")}),
        (
            "Counts",
            {"fields": ("notices_collected", "notices_saved", "notices_duplicated", "notices_failed")},
        ),
        ("Timing", {"fields": ("started_at", "finished_at", "duration_display", "success_rate_display")}),
        ("Errors", {"fields": ("error_message", "error_traceback"), "classes": ("collapse",)}),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj: CrawlerLog):
        return render_badge(obj.status, STATUS_COLORS.get(obj.status, "#6b7280"))

    @admin.display(description="Duration")
    def duration_display(self, obj: CrawlerLog):
        return f"{obj.duration_seconds:.2f}s"

    @admin.display(description="Save rate")
    def success_rate_display(self, obj: CrawlerLog):
        return f"{obj.success_rate:.1f}%"


@admin.register(CrawlerStatus)
class CrawlerStatusAdmin(admin.ModelAdmin):
    list_display = (
        "agency",
        "last_status_badge",
        "total_crawls",
        "successful_crawls",
        "failed_crawls",
        "partial_crawls",
        "total_notices_saved",
        "success_rate_display",
        "last_crawled_at",
    )
    list_filter = ("last_status", "last_crawled_at")
    search_fields = ("agency__name", "agency__code", "last_error_message")
    ordering = ("-last_crawled_at",)
    list_select_related = ("agency",)
    readonly_fields = (
        "agency",
        "total_crawls",
        "successful_crawls",
        "failed_crawls",
        "partial_crawls",
        "total_notices_collected",
        "total_notices_saved",
        "average_crawl_time",
        "last_status",
        "last_error_message",
        "last_crawled_at",
        "created_at",
        "updated_at",
        "success_rate_display",
        "average_save_rate_display",
    )

    fieldsets = (
        ("Agency", {"fields": ("agency", "last_status", "last_crawled_at", "last_error_message")}),
        (
            "Runs",
            {"fields": ("total_crawls", "successful_crawls", "failed_crawls", "partial_crawls")},
        ),
        (
            "Collection",
            {
                "fields": (
                    "total_notices_collected",
                    "total_notices_saved",
                    "success_rate_display",
                    "average_save_rate_display",
                    "average_crawl_time",
                )
            },
        ),
        ("Metadata", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def has_add_permission(self, request):
        return False

    @admin.display(description="Status", ordering="last_status")
    def last_status_badge(self, obj: CrawlerStatus):
        return render_badge(obj.last_status or "never", STATUS_COLORS.get(obj.last_status, "#6b7280"))

    @admin.display(description="Success rate")
    def success_rate_display(self, obj: CrawlerStatus):
        return f"{obj.success_rate:.1f}%"

    @admin.display(description="Save rate")
    def average_save_rate_display(self, obj: CrawlerStatus):
        return f"{obj.average_save_rate:.1f}%"


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "notice", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "user__email", "notice__title")
    raw_id_fields = ("user", "notice")
    readonly_fields = ("created_at",)


@admin.register(WatchTag)
class WatchTagAdmin(admin.ModelAdmin):
    list_display = ("user", "tag", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("user__username", "user__email", "tag")
    raw_id_fields = ("user",)
    readonly_fields = ("created_at",)


@admin.register(WatchAgency)
class WatchAgencyAdmin(admin.ModelAdmin):
    list_display = ("user", "agency", "is_active", "created_at")
    list_filter = ("is_active", "agency", "created_at")
    search_fields = ("user__username", "user__email", "agency__name", "agency__code")
    raw_id_fields = ("user", "agency")
    readonly_fields = ("created_at",)


@admin.register(EmailSubscription)
class EmailSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("email", "keywords", "is_active", "last_sent_at", "created_at")
    list_filter = ("is_active", "created_at", "last_sent_at", "agencies")
    search_fields = ("email", "keywords", "agencies__name", "agencies__code")
    filter_horizontal = ("agencies",)
    readonly_fields = ("last_sent_at", "created_at", "updated_at")
    actions = ("activate_subscriptions", "deactivate_subscriptions")

    @admin.action(description="Activate selected subscriptions")
    def activate_subscriptions(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"Activated {count} subscriptions.", level=messages.SUCCESS)

    @admin.action(description="Deactivate selected subscriptions")
    def deactivate_subscriptions(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {count} subscriptions.", level=messages.WARNING)


@admin.register(EmailNotificationLog)
class EmailNotificationLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "subscription", "notice", "status", "sent_at")
    list_filter = ("status", "created_at", "sent_at", "notice__agency")
    search_fields = ("subscription__email", "notice__title", "matched_keywords", "error_message")
    raw_id_fields = ("subscription", "notice")
    readonly_fields = ("subscription", "notice", "status", "matched_keywords", "error_message", "sent_at", "created_at")

    def has_add_permission(self, request):
        return False


class NoticeInline(admin.TabularInline):
    model = Notice
    extra = 0
    fields = ("title", "category", "posted_date", "deadline")
    readonly_fields = fields
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


AgencyAdmin.inlines = (NoticeInline,)
