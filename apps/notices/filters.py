from __future__ import annotations

import django_filters
from django.db.models import Q

from .constants import CRAWLER_METHOD_CHOICES, VISIBLE_NOTICE_CATEGORIES
from .models import Agency, Notice


class NoticeFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")
    title = django_filters.CharFilter(field_name="title", lookup_expr="icontains")
    content = django_filters.CharFilter(field_name="content", lookup_expr="icontains")
    agency = django_filters.CharFilter(field_name="agency__code", lookup_expr="iexact")
    category = django_filters.ChoiceFilter(choices=VISIBLE_NOTICE_CATEGORIES)
    tag = django_filters.CharFilter(method="filter_tag")
    is_deadline_soon = django_filters.BooleanFilter()
    posted_date_start = django_filters.DateFilter(field_name="posted_date", lookup_expr="gte")
    posted_date_end = django_filters.DateFilter(field_name="posted_date", lookup_expr="lte")
    deadline_start = django_filters.DateFilter(field_name="deadline", lookup_expr="gte")
    deadline_end = django_filters.DateFilter(field_name="deadline", lookup_expr="lte")
    ordering = django_filters.OrderingFilter(
        fields=(
            ("posted_date", "posted_date"),
            ("deadline", "deadline"),
            ("importance_score", "importance_score"),
            ("rule_score", "rule_score"),
            ("created_at", "created_at"),
        )
    )

    class Meta:
        model = Notice
        fields = [
            "search",
            "title",
            "content",
            "agency",
            "category",
            "tag",
            "is_deadline_soon",
            "posted_date_start",
            "posted_date_end",
            "deadline_start",
            "deadline_end",
        ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(title__icontains=value)
            | Q(content__icontains=value)
            | Q(summary__icontains=value)
            | Q(ai_summary__icontains=value)
            | Q(ai_tags__icontains=value)
        )

    def filter_tag(self, queryset, name, value):
        return queryset.filter(ai_tags__icontains=value)


class AgencyFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    is_active = django_filters.BooleanFilter()
    crawler_method = django_filters.ChoiceFilter(choices=CRAWLER_METHOD_CHOICES)

    class Meta:
        model = Agency
        fields = ["name", "is_active", "crawler_method"]
