"""
REST Framework Serializer

공고 및 기관 정보의 직렬화
"""
from rest_framework import serializers
from .models import Agency, Notice, CrawlerLog, CrawlerStatus
from .constants import AI_TAGS_KR, EXCLUDED_NOTICE_CATEGORIES


class AgencySerializer(serializers.ModelSerializer):
    """기관 정보 시리얼라이저"""
    
    total_notices = serializers.SerializerMethodField()
    last_crawl_status_display = serializers.CharField(
        source='get_last_crawl_status_display', 
        read_only=True
    )
    crawler_method_display = serializers.CharField(
        source='get_crawler_method_display',
        read_only=True
    )
    
    class Meta:
        model = Agency
        fields = [
            'code', 'name', 'name_en', 'description',
            'website_url', 'notice_url', 'api_url', 'rss_url',
            'is_active', 'crawler_method', 'crawler_method_display',
            'total_notices', 'last_crawl_at', 'last_crawl_status',
            'last_crawl_status_display', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'code', 'total_notices', 'last_crawl_at',
            'created_at', 'updated_at',
        ]
    
    def get_total_notices(self, obj):
        """활성 공고 수"""
        return obj.notices.filter(is_deleted=False).exclude(
            category__in=EXCLUDED_NOTICE_CATEGORIES
        ).count()


class NoticeListSerializer(serializers.ModelSerializer):
    """공고 목록 시리얼라이저 (요약 정보)"""
    
    agency_name = serializers.CharField(source='agency.name', read_only=True)
    agency_code = serializers.CharField(source='agency.code', read_only=True)
    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True
    )
    days_to_deadline = serializers.SerializerMethodField()
    ai_tags_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Notice
        fields = [
            'id', 'agency_code', 'agency_name', 'title', 'url',
            'posted_date', 'deadline', 'days_to_deadline',
            'is_deadline_soon', 'category', 'category_display',
            'ai_summary', 'ai_tags', 'ai_tags_display',
            'rule_score', 'importance_score', 'score_source',
            'ai_analysis_status', 'recommended_for',
            'bookmark_count', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'bookmark_count']
    
    def get_days_to_deadline(self, obj):
        """마감까지 남은 일수"""
        return obj.days_to_deadline
    
    def get_ai_tags_display(self, obj):
        """AI 태그를 한글로 표시"""
        if not obj.ai_tags:
            return []
        return [AI_TAGS_KR.get(tag, tag) for tag in obj.ai_tags]


class NoticeDetailSerializer(serializers.ModelSerializer):
    """공고 상세 시리얼라이저"""
    
    agency_data = AgencySerializer(source='agency', read_only=True)
    agency_name = serializers.CharField(source='agency.name', read_only=True)
    agency_code = serializers.CharField(source='agency.code', read_only=True)
    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True
    )
    days_to_deadline = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    ai_tags_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Notice
        fields = [
            'id', 'agency_code', 'agency_name', 'agency_data',
            'title', 'content', 'summary', 'url',
            'posted_date', 'deadline', 'days_to_deadline', 'is_expired',
            'is_deadline_soon', 'category', 'category_display',
            'ai_summary', 'ai_tags', 'ai_tags_display',
            'rule_score', 'importance_score', 'score_source',
            'ai_analysis_status', 'recommended_for', 'bookmark_count',
            'created_at', 'updated_at', 'ai_analyzed_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'ai_analyzed_at',
            'bookmark_count',
        ]
    
    def get_days_to_deadline(self, obj):
        """마감까지 남은 일수"""
        return obj.days_to_deadline
    
    def get_is_expired(self, obj):
        """만료 여부"""
        return obj.is_expired
    
    def get_ai_tags_display(self, obj):
        """AI 태그를 한글로 표시"""
        if not obj.ai_tags:
            return []
        return [AI_TAGS_KR.get(tag, tag) for tag in obj.ai_tags]


class CrawlerLogSerializer(serializers.ModelSerializer):
    """크롤러 로그 시리얼라이저"""
    
    agency_name = serializers.CharField(source='agency.name', read_only=True)
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    duration_minutes = serializers.SerializerMethodField()
    success_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = CrawlerLog
        fields = [
            'id', 'agency_name', 'status', 'status_display',
            'notices_collected', 'notices_saved', 'notices_duplicated',
            'error_message', 'start_time', 'end_time',
            'duration_minutes', 'success_rate', 'created_at',
        ]
        read_only_fields = [
            'id', 'agency_name', 'notices_collected', 'notices_saved',
            'notices_duplicated', 'error_message', 'start_time', 'end_time',
            'created_at',
        ]
    
    def get_duration_minutes(self, obj):
        """크롤링 소요 시간 (분)"""
        return obj.duration_minutes
    
    def get_success_rate(self, obj):
        """성공률"""
        return obj.success_rate


class CrawlerStatusSerializer(serializers.ModelSerializer):
    """크롤러 통계 시리얼라이저"""
    
    agency_name = serializers.CharField(source='agency.name', read_only=True)
    last_status_display = serializers.CharField(
        source='get_last_status_display',
        read_only=True
    )
    success_rate = serializers.SerializerMethodField()
    average_save_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = CrawlerStatus
        fields = [
            'agency_name', 'total_crawls', 'successful_crawls',
            'failed_crawls', 'partial_crawls', 'total_notices_collected',
            'total_notices_saved', 'average_crawl_time',
            'last_status', 'last_status_display', 'last_crawled_at',
            'success_rate', 'average_save_rate', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'agency_name', 'total_crawls', 'successful_crawls',
            'failed_crawls', 'partial_crawls', 'total_notices_collected',
            'total_notices_saved', 'average_crawl_time',
            'last_crawled_at', 'created_at', 'updated_at',
        ]
    
    def get_success_rate(self, obj):
        """성공률"""
        return obj.success_rate
    
    def get_average_save_rate(self, obj):
        """평균 저장률"""
        return obj.average_save_rate
