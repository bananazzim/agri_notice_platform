from __future__ import annotations

from typing import Any

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, ListView, TemplateView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from services.ai_service import NoticeAIService

from .constants import EXCLUDED_NOTICE_CATEGORIES, VISIBLE_NOTICE_CATEGORIES
from .filters import AgencyFilter, NoticeFilter
from .models import Agency, CrawlerLog, CrawlerStatus, Notice
from .serializers import (
    AgencySerializer,
    CrawlerLogSerializer,
    CrawlerStatusSerializer,
    NoticeDetailSerializer,
    NoticeListSerializer,
)


ORDERING_MAP = {
    "latest": ("-posted_date", "-created_at"),
    "deadline": ("deadline", "-posted_date"),
    "importance": ("-importance_score", "-posted_date", "-created_at"),
}


def get_notice_queryset(params: dict[str, Any] | None = None):
    params = params or {}
    queryset = Notice.objects.active().select_related("agency")

    query = params.get("q") or params.get("search")
    if query:
        queryset = queryset.filter(
            Q(title__icontains=query)
            | Q(content__icontains=query)
            | Q(summary__icontains=query)
            | Q(ai_summary__icontains=query)
            | Q(ai_tags__icontains=query)
        )

    agency = params.get("agency")
    if agency:
        queryset = queryset.filter(agency__code=agency)

    category = params.get("category")
    if category:
        queryset = queryset.filter(category=category)

    tag = params.get("tag") or params.get("tags")
    if tag:
        queryset = queryset.filter(ai_tags__icontains=tag)

    if str(params.get("deadline_soon") or params.get("is_deadline_soon")).lower() in {"1", "true", "yes"}:
        queryset = queryset.deadline_soon()

    posted_from = params.get("posted_from") or params.get("posted_date_start")
    if posted_from:
        queryset = queryset.filter(posted_date__gte=posted_from)

    posted_to = params.get("posted_to") or params.get("posted_date_end")
    if posted_to:
        queryset = queryset.filter(posted_date__lte=posted_to)

    deadline_from = params.get("deadline_from") or params.get("deadline_start")
    if deadline_from:
        queryset = queryset.filter(deadline__gte=deadline_from)

    deadline_to = params.get("deadline_to") or params.get("deadline_end")
    if deadline_to:
        queryset = queryset.filter(deadline__lte=deadline_to)

    ordering = params.get("ordering") or "latest"
    return queryset.order_by(*ORDERING_MAP.get(ordering, ORDERING_MAP["latest"]))


class NoticeListView(ListView):
    model = Notice
    template_name = "notices/notice_list.html"
    context_object_name = "notices"
    paginate_by = 20

    def get_queryset(self):
        return get_notice_queryset(self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET
        active_notices = Notice.objects.active()
        context.update(
            {
                "agencies": Agency.objects.filter(is_active=True).order_by("crawler_priority", "name"),
                "categories": VISIBLE_NOTICE_CATEGORIES,
                "selected": {
                    "q": params.get("q") or params.get("search") or "",
                    "agency": params.get("agency", ""),
                    "category": params.get("category", ""),
                    "tag": params.get("tag") or params.get("tags") or "",
                    "ordering": params.get("ordering", "latest"),
                    "posted_from": params.get("posted_from") or params.get("posted_date_start") or "",
                    "posted_to": params.get("posted_to") or params.get("posted_date_end") or "",
                    "deadline_soon": params.get("deadline_soon") or params.get("is_deadline_soon") or "",
                },
                "total_notices_count": active_notices.count(),
                "deadline_soon_count": active_notices.deadline_soon().count(),
                "agency_count": Agency.objects.filter(is_active=True).count(),
                "ai_success_count": active_notices.filter(ai_analysis_status="success").count(),
                "recommended_count": active_notices.filter(importance_score__gte=70).count(),
            }
        )
        return context


class DeadlineSoonNoticeListView(NoticeListView):
    template_name = "notices/deadline_soon.html"

    def get_queryset(self):
        params = self.request.GET.copy()
        params["deadline_soon"] = "true"
        return get_notice_queryset(params)


class NoticeDetailView(DetailView):
    model = Notice
    template_name = "notices/notice_detail.html"
    context_object_name = "notice"
    ai_outcome = None

    def get_queryset(self):
        return Notice.objects.active().select_related("agency")

    def get_object(self, queryset=None):
        notice = super().get_object(queryset)
        self.ai_outcome = NoticeAIService().analyze_notice(
            notice,
            user_opened_detail=True,
        )
        if self.ai_outcome.analyzed:
            notice.refresh_from_db()
        return notice

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ai_outcome"] = self.ai_outcome
        return context


class NoticeStatsView(TemplateView):
    template_name = "notices/stats.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_notices = Notice.objects.active()
        context.update(
            {
                "total_notices": active_notices.count(),
                "deadline_soon_count": active_notices.deadline_soon().count(),
                "agency_count": Agency.objects.filter(is_active=True).count(),
                "category_stats": active_notices.values("category").annotate(count=Count("id")).order_by("-count"),
                "agency_stats": Agency.objects.annotate(
                    notice_count=Count(
                        "notices",
                        filter=Q(notices__is_deleted=False)
                        & ~Q(notices__category__in=EXCLUDED_NOTICE_CATEGORIES),
                    )
                ).order_by("-notice_count")[:20],
                "recent_logs": CrawlerLog.objects.select_related("agency").order_by("-created_at")[:20],
            }
        )
        return context


class NoticeListAPIView(generics.ListAPIView):
    serializer_class = NoticeListSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = NoticeFilter
    search_fields = ["title", "content", "summary", "ai_summary", "ai_tags"]
    ordering_fields = ["posted_date", "deadline", "importance_score", "rule_score", "created_at"]
    ordering = ["-posted_date", "-created_at"]

    def get_queryset(self):
        return Notice.objects.active().select_related("agency")


class NoticeDetailAPIView(generics.RetrieveAPIView):
    serializer_class = NoticeDetailSerializer
    lookup_field = "pk"

    def get_queryset(self):
        return Notice.objects.active().select_related("agency")


class AgencyListAPIView(generics.ListAPIView):
    serializer_class = AgencySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = AgencyFilter
    search_fields = ["name", "name_en", "code"]
    ordering_fields = ["crawler_priority", "name", "total_notices", "last_crawl_at"]
    ordering = ["crawler_priority", "name"]

    def get_queryset(self):
        return Agency.objects.all()


class AgencyDetailAPIView(generics.RetrieveAPIView):
    serializer_class = AgencySerializer
    lookup_field = "code"

    def get_queryset(self):
        return Agency.objects.all()


class CrawlerLogListAPIView(generics.ListAPIView):
    serializer_class = CrawlerLogSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["agency__name", "agency__code", "error_message"]
    ordering_fields = ["created_at", "status", "notices_saved", "notices_collected"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return CrawlerLog.objects.select_related("agency")


class CrawlerStatusListAPIView(generics.ListAPIView):
    serializer_class = CrawlerStatusSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["agency__name", "agency__code"]
    ordering_fields = ["last_crawled_at", "total_crawls", "total_notices_saved", "average_crawl_time"]
    ordering = ["-last_crawled_at"]

    def get_queryset(self):
        return CrawlerStatus.objects.select_related("agency")


@api_view(["POST"])
def increment_notice_view(request, pk):
    notice = get_object_or_404(Notice.objects.active(), pk=pk)
    return Response({"id": str(notice.pk), "detail": "view count is disabled"}, status=status.HTTP_200_OK)
