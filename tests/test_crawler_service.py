import pytest
from unittest.mock import Mock, patch
from django.utils import timezone

from services.crawler_service import CrawlerService
from apps.notices.models import Agency, Notice, CrawlerLog, CrawlerStatus
from crawlers.registry import CrawlerRegistry


@pytest.mark.django_db
class TestCrawlerService:
    @pytest.fixture(autouse=True)
    def service(self):
        return CrawlerService()

    @patch.object(CrawlerRegistry, 'get')
    def test_crawl_agency_saves_notices(self, mock_get, service):
        fake_crawler = Mock()
        fake_crawler.agency_code = 'test'
        fake_crawler.agency_name = '테스트 기관'
        fake_crawler.website_url = 'https://test.go.kr'
        fake_crawler.notice_url = 'https://test.go.kr/notice'
        fake_crawler.api_url = 'https://test.go.kr/api'
        fake_crawler.rss_url = 'https://test.go.kr/rss'
        fake_crawler.crawler_method = 'rss'
        fake_crawler.crawl.return_value = {
            'status': 'success',
            'notices': [
                {
                    'title': '공고 1',
                    'content': '내용 1',
                    'summary': '요약 1',
                    'url': 'https://test.go.kr/notice/1',
                    'posted_date': '2024-06-15',
                    'deadline': '2024-07-15',
                    'category': 'support',
                    'importance_score': 70,
                    'ai_tags': ['tag1'],
                    'recommended_for': ['student'],
                }
            ],
            'count': 1,
            'start_time': timezone.now(),
            'end_time': timezone.now(),
            'duration': 0.5,
            'error': None,
        }
        mock_get.return_value = fake_crawler

        saved_count = service.crawl_agency('test')

        assert saved_count == 1
        assert Notice.objects.count() == 1
        assert CrawlerLog.objects.count() == 1
        assert CrawlerStatus.objects.count() == 1

        notice = Notice.objects.first()
        assert notice.rule_score == 8
        assert notice.importance_score == 8
        assert notice.score_source == 'rule'
        assert notice.ai_analysis_status == 'skipped'

        log = CrawlerLog.objects.first()
        assert log.notices_collected == 1
        assert log.notices_saved == 1
        assert log.notices_duplicated == 0

        status = CrawlerStatus.objects.first()
        assert status.total_crawls == 1
        assert status.successful_crawls == 1

    @patch.object(CrawlerRegistry, 'get')
    def test_crawl_agency_duplicate_notice(self, mock_get, service):
        agency = Agency.objects.create(
            code='test',
            name='테스트 기관',
            website_url='https://test.go.kr',
        )
        Notice.objects.create(
            agency=agency,
            title='공고 1',
            content='내용 1',
            summary_raw='요약 1',
            url='https://test.go.kr/notice/1',
            posted_date=timezone.now().date(),
        )

        fake_crawler = Mock()
        fake_crawler.agency_code = 'test'
        fake_crawler.agency_name = '테스트 기관'
        fake_crawler.website_url = 'https://test.go.kr'
        fake_crawler.notice_url = 'https://test.go.kr/notice'
        fake_crawler.api_url = 'https://test.go.kr/api'
        fake_crawler.rss_url = 'https://test.go.kr/rss'
        fake_crawler.crawler_method = 'rss'
        fake_crawler.crawl.return_value = {
            'status': 'success',
            'notices': [
                {
                    'title': '공고 1',
                    'content': '내용 1',
                    'summary': '요약 1',
                    'url': 'https://test.go.kr/notice/1',
                    'posted_date': '2024-06-15',
                    'deadline': '2024-07-15',
                    'category': 'support',
                    'importance_score': 70,
                    'ai_tags': ['tag1'],
                    'recommended_for': ['student'],
                }
            ],
            'count': 1,
            'start_time': timezone.now(),
            'end_time': timezone.now(),
            'duration': 0.5,
            'error': None,
        }
        mock_get.return_value = fake_crawler

        saved_count = service.crawl_agency('test')

        assert saved_count == 0
        assert Notice.objects.count() == 1
        notice = Notice.objects.get(url='https://test.go.kr/notice/1')
        assert notice.deadline.isoformat() == '2024-07-15'
        log = CrawlerLog.objects.first()
        assert log.notices_saved == 0
        assert log.notices_duplicated == 1

    @patch.object(CrawlerRegistry, 'get')
    def test_crawl_agency_skips_news_category(self, mock_get, service):
        fake_crawler = Mock()
        fake_crawler.agency_code = 'test'
        fake_crawler.agency_name = 'Test Agency'
        fake_crawler.website_url = 'https://test.go.kr'
        fake_crawler.notice_url = 'https://test.go.kr/notice'
        fake_crawler.api_url = ''
        fake_crawler.rss_url = ''
        fake_crawler.crawler_method = 'html'
        fake_crawler.crawl.return_value = {
            'status': 'success',
            'notices': [
                {
                    'title': '뉴스성 공지',
                    'content': '뉴스 내용',
                    'summary': '뉴스 요약',
                    'url': 'https://test.go.kr/news/1',
                    'posted_date': '2024-06-15',
                    'deadline': None,
                    'category': 'news',
                    'importance_score': 50,
                    'ai_tags': [],
                    'recommended_for': [],
                }
            ],
            'count': 1,
            'start_time': timezone.now(),
            'end_time': timezone.now(),
            'duration': 0.5,
            'error': None,
        }
        mock_get.return_value = fake_crawler

        saved_count = service.crawl_agency('test')

        assert saved_count == 0
        assert Notice.objects.count() == 0
        assert Agency.objects.get(code='test').total_notices == 0

    @patch.object(CrawlerRegistry, 'get_codes')
    @patch.object(CrawlerRegistry, 'get')
    def test_crawl_all_runs_all_crawlers(self, mock_get, mock_get_codes, service):
        mock_get_codes.return_value = ['a', 'b']

        first_crawler = Mock()
        first_crawler.agency_code = 'a'
        first_crawler.agency_name = '기관 A'
        first_crawler.website_url = 'https://a.go.kr'
        first_crawler.notice_url = 'https://a.go.kr/notice'
        first_crawler.api_url = ''
        first_crawler.rss_url = ''
        first_crawler.crawler_method = 'api'
        first_crawler.crawl.return_value = {
            'status': 'success',
            'notices': [
                {'title': 'A1', 'content': 'A1', 'summary': 'A1', 'url': 'https://a.go.kr/1', 'posted_date': '2024-06-15', 'deadline': None, 'category': 'support', 'importance_score': 50, 'ai_tags': [], 'recommended_for': []}
            ],
            'count': 1,
            'start_time': timezone.now(),
            'end_time': timezone.now(),
            'duration': 0.1,
            'error': None,
        }

        second_crawler = Mock()
        second_crawler.agency_code = 'b'
        second_crawler.agency_name = '기관 B'
        second_crawler.website_url = 'https://b.go.kr'
        second_crawler.notice_url = 'https://b.go.kr/notice'
        second_crawler.api_url = ''
        second_crawler.rss_url = ''
        second_crawler.crawler_method = 'api'
        second_crawler.crawl.return_value = {
            'status': 'success',
            'notices': [
                {'title': 'B1', 'content': 'B1', 'summary': 'B1', 'url': 'https://b.go.kr/1', 'posted_date': '2024-06-16', 'deadline': None, 'category': 'education', 'importance_score': 50, 'ai_tags': [], 'recommended_for': []}
            ],
            'count': 1,
            'start_time': timezone.now(),
            'end_time': timezone.now(),
            'duration': 0.1,
            'error': None,
        }

        def get_crawler(code):
            return first_crawler if code == 'a' else second_crawler

        mock_get.side_effect = get_crawler

        total_saved = service.crawl_all()

        assert total_saved == 2
        assert Notice.objects.count() == 2
        assert CrawlerLog.objects.count() == 2
        assert CrawlerStatus.objects.count() == 2
