"""
공고 모델 테스트

Notice, Agency, CrawlerLog 모델의 기능 테스트
"""
import pytest
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError

from apps.notices.models import Agency, Notice, CrawlerLog, CrawlerStatus


@pytest.mark.django_db
class TestAgencyModel:
    """기관 모델 테스트"""
    
    def test_create_agency(self):
        """기관 생성 테스트"""
        agency = Agency.objects.create(
            code='rda',
            name='농촌진흥청',
            website_url='https://www.rda.go.kr',
            crawler_method='api',
        )
        
        assert agency.code == 'rda'
        assert agency.name == '농촌진흥청'
        assert str(agency) == "농촌진흥청 (rda)"
    
    def test_agency_unique_code(self):
        """기관 코드 유니크 테스트"""
        Agency.objects.create(
            code='rda',
            name='농촌진흥청',
            website_url='https://www.rda.go.kr',
        )
        
        with pytest.raises(Exception):
            Agency.objects.create(
                code='rda',
                name='다른기관',
                website_url='https://other.go.kr',
            )


@pytest.mark.django_db
class TestNoticeModel:
    """공고 모델 테스트"""
    
    @pytest.fixture
    def agency(self):
        """테스트 기관"""
        return Agency.objects.create(
            code='test',
            name='테스트기관',
            website_url='https://test.go.kr',
        )
    
    def test_create_notice(self, agency):
        """공고 생성 테스트"""
        notice = Notice.objects.create(
            agency=agency,
            title='테스트 공고',
            content='테스트 내용',
            url='https://test.go.kr/notice/1',
            posted_date=timezone.now().date(),
            category='support',
        )
        
        assert notice.agency == agency
        assert notice.rule_score == 0
        assert notice.score_source == 'rule'
        assert notice.ai_analysis_status == 'pending'
        assert notice.ai_analysis_error == ''
        assert notice.title == '테스트 공고'
        assert notice.importance_score == 50  # 기본값
    
    def test_notice_url_unique(self, agency):
        """공고 URL 유니크 테스트"""
        Notice.objects.create(
            agency=agency,
            title='공고1',
            content='내용',
            url='https://test.go.kr/notice/1',
            posted_date=timezone.now().date(),
        )
        
        with pytest.raises(Exception):
            Notice.objects.create(
                agency=agency,
                title='공고2',
                content='내용',
                url='https://test.go.kr/notice/1',
                posted_date=timezone.now().date(),
            )
    
    def test_days_to_deadline(self, agency):
        """마감까지 남은 일수 계산"""
        today = timezone.now().date()
        deadline = today + timedelta(days=10)
        
        notice = Notice.objects.create(
            agency=agency,
            title='공고',
            content='내용',
            url='https://test.go.kr/notice/1',
            posted_date=today,
            deadline=deadline,
        )
        
        assert notice.days_to_deadline == 10
    
    def test_is_expired(self, agency):
        """만료 여부 확인"""
        today = timezone.now().date()
        
        # 만료되지 않은 공고
        future_notice = Notice.objects.create(
            agency=agency,
            title='미래 공고',
            content='내용',
            url='https://test.go.kr/notice/1',
            posted_date=today,
            deadline=today + timedelta(days=10),
        )
        assert not future_notice.is_expired
        
        # 만료된 공고
        past_notice = Notice.objects.create(
            agency=agency,
            title='과거 공고',
            content='내용',
            url='https://test.go.kr/notice/2',
            posted_date=today - timedelta(days=20),
            deadline=today - timedelta(days=10),
        )
        assert past_notice.is_expired
    
    def test_update_deadline_soon_flag(self, agency):
        """마감 임박 플래그 업데이트"""
        today = timezone.now().date()
        
        # 7일 이내 마감
        notice = Notice.objects.create(
            agency=agency,
            title='공고',
            content='내용',
            url='https://test.go.kr/notice/1',
            posted_date=today,
            deadline=today + timedelta(days=5),
        )
        notice.update_deadline_soon_flag()
        assert notice.is_deadline_soon
    
    def test_queryset_active(self, agency):
        """활성 공고 쿼리셋 테스트"""
        notice = Notice.objects.create(
            agency=agency,
            title='공고',
            content='내용',
            url='https://test.go.kr/notice/1',
            posted_date=timezone.now().date(),
        )
        
        # 활성 공고
        assert notice in Notice.objects.active()
        
        # 삭제된 공고 제외
        notice.is_deleted = True
        notice.save()
        assert notice not in Notice.objects.active()

    def test_queryset_active_excludes_news(self, agency):
        news_notice = Notice.objects.create(
            agency=agency,
            title='뉴스성 공지',
            content='뉴스 내용',
            url='https://test.go.kr/news/1',
            posted_date=timezone.now().date(),
            category='news',
        )

        assert news_notice not in Notice.objects.active()
    
    def test_queryset_by_agency(self, agency):
        """기관별 공고 쿼리셋 테스트"""
        other_agency = Agency.objects.create(
            code='other',
            name='다른기관',
            website_url='https://other.go.kr',
        )
        
        notice1 = Notice.objects.create(
            agency=agency,
            title='공고1',
            content='내용',
            url='https://test.go.kr/notice/1',
            posted_date=timezone.now().date(),
        )
        notice2 = Notice.objects.create(
            agency=other_agency,
            title='공고2',
            content='내용',
            url='https://other.go.kr/notice/1',
            posted_date=timezone.now().date(),
        )
        
        assert notice1 in Notice.objects.by_agency('test')
        assert notice2 not in Notice.objects.by_agency('test')
    
    def test_queryset_high_importance(self, agency):
        """중요도 높은 공고 쿼리셋 테스트"""
        high_notice = Notice.objects.create(
            agency=agency,
            title='중요 공고',
            content='내용',
            url='https://test.go.kr/notice/1',
            posted_date=timezone.now().date(),
            importance_score=85,
        )
        low_notice = Notice.objects.create(
            agency=agency,
            title='일반 공고',
            content='내용',
            url='https://test.go.kr/notice/2',
            posted_date=timezone.now().date(),
            importance_score=40,
        )
        
        important = Notice.objects.high_importance(70)
        assert high_notice in important
        assert low_notice not in important


@pytest.mark.django_db
class TestCrawlerLogModel:
    """크롤러 로그 모델 테스트"""
    
    @pytest.fixture
    def agency(self):
        """테스트 기관"""
        return Agency.objects.create(
            code='test',
            name='테스트기관',
            website_url='https://test.go.kr',
        )
    
    def test_create_crawler_log(self, agency):
        """크롤러 로그 생성 테스트"""
        now = timezone.now()
        
        log = CrawlerLog.objects.create(
            agency=agency,
            status='success',
            notices_collected=10,
            notices_saved=8,
            notices_duplicated=2,
            start_time=now,
            end_time=now + timedelta(minutes=5),
        )
        
        assert log.status == 'success'
        assert log.notices_collected == 10
    
    def test_crawler_log_duration(self, agency):
        """크롤러 로그 소요 시간 계산"""
        start = timezone.now()
        end = start + timedelta(minutes=5)
        
        log = CrawlerLog.objects.create(
            agency=agency,
            status='success',
            start_time=start,
            end_time=end,
        )
        
        assert log.duration_seconds == 300
        assert log.duration_minutes == 5.0
    
    def test_crawler_log_success_rate(self, agency):
        """크롤러 로그 성공률 계산"""
        now = timezone.now()
        
        log = CrawlerLog.objects.create(
            agency=agency,
            status='success',
            notices_collected=10,
            notices_saved=8,
            start_time=now,
            end_time=now,
        )
        
        assert log.success_rate == 80.0


@pytest.mark.django_db
class TestCrawlerStatusModel:
    """크롤러 통계 모델 테스트"""
    
    @pytest.fixture
    def agency(self):
        """테스트 기관"""
        return Agency.objects.create(
            code='test',
            name='테스트기관',
            website_url='https://test.go.kr',
        )
    
    def test_create_crawler_status(self, agency):
        """크롤러 통계 생성 테스트"""
        status = CrawlerStatus.objects.create(
            agency=agency,
            total_crawls=10,
            successful_crawls=8,
            failed_crawls=1,
            partial_crawls=1,
        )
        
        assert status.agency == agency
        assert status.total_crawls == 10
    
    def test_crawler_status_success_rate(self, agency):
        """크롤러 통계 성공률"""
        status = CrawlerStatus.objects.create(
            agency=agency,
            total_crawls=10,
            successful_crawls=8,
            failed_crawls=2,
        )
        
        assert status.success_rate == 80.0
