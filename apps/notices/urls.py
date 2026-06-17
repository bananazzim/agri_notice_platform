from django.urls import path

from . import views

app_name = "notices"

urlpatterns = [
    path("", views.NoticeListView.as_view(), name="notice_list"),
    path("deadline-soon/", views.DeadlineSoonNoticeListView.as_view(), name="deadline_soon"),
    path("stats/", views.NoticeStatsView.as_view(), name="stats"),
    path("<uuid:pk>/", views.NoticeDetailView.as_view(), name="notice_detail"),
    path("api/notices/", views.NoticeListAPIView.as_view(), name="api_notice_list"),
    path("api/notices/<uuid:pk>/", views.NoticeDetailAPIView.as_view(), name="api_notice_detail"),
    path("api/notices/<uuid:pk>/view/", views.increment_notice_view, name="api_notice_view"),
    path("api/agencies/", views.AgencyListAPIView.as_view(), name="api_agency_list"),
    path("api/agencies/<slug:code>/", views.AgencyDetailAPIView.as_view(), name="api_agency_detail"),
    path("api/crawler-logs/", views.CrawlerLogListAPIView.as_view(), name="api_crawler_log_list"),
    path("api/crawler-status/", views.CrawlerStatusListAPIView.as_view(), name="api_crawler_status_list"),
]
