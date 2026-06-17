"""
BaseCrawler 테스트

크롤러 기본 기능 및 유틸리티 함수 테스트
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from crawlers.base import BaseCrawler
from crawlers.registry import CrawlerRegistry, register_crawler
from core.exceptions import (
    CrawlerConnectionError,
    CrawlerParseError,
    CrawlerNotImplementedError,
)
from core.utils import (
    normalize_url,
    normalize_date,
    clean_text,
    extract_domain,
    is_deadline_soon,
    calculate_days_to_deadline,
)


# ========== BaseCrawler 테스트 ==========

class TestCrawler(BaseCrawler):
    """테스트용 크롤러 구현"""
    agency_name = "Test Agency"
    agency_code = "test"
    website_url = "https://test.go.kr"
    
    def fetch_notices(self):
        """테스트 공고 반환"""
        return [
            {
                'title': '테스트 공고 1',
                'url': 'https://test.go.kr/notice/1',
                'posted_date': '2024-06-15',
                'deadline': '2024-07-15',
                'content': '테스트 내용',
            }
        ]


class TestBaseCrawler:
    """BaseCrawler 테스트"""
    
    @pytest.fixture
    def crawler(self):
        """테스트 크롤러"""
        return TestCrawler()
    
    def test_crawler_initialization(self, crawler):
        """크롤러 초기화"""
        assert crawler.agency_code == "test"
        assert crawler.agency_name == "Test Agency"
        assert crawler.session is not None
    
    def test_normalize_url(self):
        """URL 정규화"""
        # 기본 URL 정규화
        url = "https://example.com/path?b=2&a=1"
        normalized = normalize_url(url)
        assert normalized.startswith("https://")
        
        # 상대 URL 변환
        relative_url = "/path/to/page"
        base_url = "https://example.com"
        normalized = normalize_url(relative_url, base_url)
        assert normalized == "https://example.com/path/to/page"
        
        # 스킴 없는 URL
        url_no_scheme = "example.com/path"
        normalized = normalize_url(url_no_scheme)
        assert normalized.startswith("https://")
    
    def test_normalize_date(self):
        """날짜 정규화"""
        # 다양한 형식 처리
        test_cases = [
            ("2024-06-15", "2024-06-15"),
            ("2024/06/15", "2024-06-15"),
            ("2024.06.15", "2024-06-15"),
            ("20240615", "2024-06-15"),
        ]
        
        for input_date, expected in test_cases:
            result = normalize_date(input_date)
            assert result == expected
        
        # 잘못된 날짜
        result = normalize_date("invalid")
        assert result is None
    
    def test_clean_text(self):
        """텍스트 정제"""
        # 여러 줄 공백 정리
        text = "테스트   문자열\n\n   공백"
        cleaned = clean_text(text)
        assert cleaned == "테스트 문자열 공백"
        
        # 앞뒤 공백 제거
        text = "  테스트  "
        cleaned = clean_text(text)
        assert cleaned == "테스트"
        
        # 빈 문자열
        assert clean_text("") == ""
    
    def test_extract_domain(self):
        """도메인 추출"""
        url = "https://www.example.com/path"
        domain = extract_domain(url)
        assert domain == "example.com"
        
        # www 제거
        url = "https://www.test.co.kr"
        domain = extract_domain(url)
        assert domain == "test.co.kr"
    
    def test_is_deadline_soon(self):
        """마감 임박 여부"""
        today = datetime.now().date()
        
        # 5일 남음 (임박)
        future_date = today + timedelta(days=5)
        assert is_deadline_soon(future_date.strftime('%Y-%m-%d'), 7)
        
        # 10일 남음 (임박 아님)
        future_date = today + timedelta(days=10)
        assert not is_deadline_soon(future_date.strftime('%Y-%m-%d'), 7)
        
        # 마감일 없음
        assert not is_deadline_soon(None)
    
    def test_calculate_days_to_deadline(self):
        """마감까지 남은 일수"""
        today = datetime.now().date()
        
        # 10일 남음
        deadline = today + timedelta(days=10)
        days = calculate_days_to_deadline(deadline.strftime('%Y-%m-%d'))
        assert days == 10
        
        # 마감일 없음
        assert calculate_days_to_deadline(None) is None
    
    def test_normalize_notice(self, crawler):
        """공고 정규화"""
        notice = {
            'agency': 'test',
            'title': '  테스트   공고  ',
            'content': '테스트\n\n내용',
            'url': 'https://test.go.kr/notice/1',
            'posted_date': '2024-06-15',
            'deadline': '2024-07-15',
            'category': 'support',
        }
        
        normalized = crawler.normalize_notice(notice)
        
        assert normalized['title'] == '테스트 공고'
        assert normalized['content'] == '테스트 내용'
        assert normalized['url'] == 'https://test.go.kr/notice/1'
        assert normalized['posted_date'] == '2024-06-15'
        assert normalized['deadline'] == '2024-07-15'
    
    def test_validate_notice(self, crawler):
        """공고 검증"""
        # 유효한 공고
        valid_notice = {
            'title': '공고',
            'url': 'https://test.go.kr/notice/1',
            'posted_date': '2024-06-15',
        }
        assert crawler.validate_notice(valid_notice)
        
        # 필드 누락
        invalid_notice = {
            'title': '공고',
            'url': 'https://test.go.kr/notice/1',
        }
        assert not crawler.validate_notice(invalid_notice)
        
        # 유효하지 않은 URL
        invalid_notice = {
            'title': '공고',
            'url': 'invalid_url',
            'posted_date': '2024-06-15',
        }
        assert not crawler.validate_notice(invalid_notice)
    
    def test_crawl(self, crawler):
        """크롤링 메인 메서드"""
        result = crawler.crawl()
        
        assert result['status'] in ['success', 'partial', 'failed']
        assert 'notices' in result
        assert 'count' in result
        assert 'duration' in result
        assert result['count'] >= 0


# ========== 크롤러 레지스트리 테스트 ==========

class TestCrawlerRegistry:
    """크롤러 레지스트리 테스트"""
    
    def test_register_crawler(self):
        """크롤러 등록"""
        CrawlerRegistry.register('test_registry', TestCrawler)
        assert CrawlerRegistry.is_registered('test_registry')
    
    def test_get_crawler(self):
        """크롤러 조회"""
        CrawlerRegistry.register('test_get', TestCrawler)
        crawler = CrawlerRegistry.get('test_get')
        
        assert crawler is not None
        assert isinstance(crawler, BaseCrawler)
    
    def test_get_nonexistent_crawler(self):
        """존재하지 않는 크롤러 조회"""
        crawler = CrawlerRegistry.get('nonexistent')
        assert crawler is None
    
    def test_list_crawlers(self):
        """크롤러 목록"""
        CrawlerRegistry.register('test_list1', TestCrawler)
        CrawlerRegistry.register('test_list2', TestCrawler)
        
        crawlers = CrawlerRegistry.list_crawlers()
        assert 'test_list1' in crawlers
        assert 'test_list2' in crawlers
    
    def test_register_crawler_decorator(self):
        """데코레이터 기반 등록"""
        @register_crawler('decorated_crawler')
        class DecoratedCrawler(BaseCrawler):
            agency_name = "Decorated"
            agency_code = "decorated"
            
            def fetch_notices(self):
                return []
        
        assert CrawlerRegistry.is_registered('decorated_crawler')
        crawler = CrawlerRegistry.get('decorated_crawler')
        assert crawler is not None


# ========== HTTP 요청 테스트 ==========

class TestCrawlerHTTP:
    """HTTP 요청 테스트"""
    
    @pytest.fixture
    def crawler(self):
        return TestCrawler()
    
    @patch('crawlers.base.requests.Session.get')
    def test_fetch_page_success(self, mock_get, crawler):
        """페이지 요청 성공"""
        mock_response = Mock()
        mock_response.text = "<html><body>Test</body></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        response = crawler.fetch_page('https://test.go.kr')
        assert response is not None
    
    @patch('crawlers.base.requests.Session.get')
    def test_fetch_page_failure(self, mock_get, crawler):
        """페이지 요청 실패"""
        import requests
        mock_get.side_effect = requests.RequestException("Connection failed")
        
        with pytest.raises(CrawlerConnectionError):
            crawler.fetch_page('https://test.go.kr')
    
    def test_parse_html(self, crawler):
        """HTML 파싱"""
        html = "<html><body><h1>Test</h1></body></html>"
        soup = crawler.parse_html(html)
        
        assert soup is not None
        assert soup.h1.string == "Test"
    
    def test_parse_html_failure(self, crawler):
        """HTML 파싱 실패"""
        with pytest.raises(CrawlerParseError):
            crawler.parse_html(None)


# ========== Context Manager 테스트 ==========

class TestCrawlerContextManager:
    """Context Manager 테스트"""
    
    def test_context_manager(self):
        """with 문 사용"""
        with TestCrawler() as crawler:
            assert crawler is not None
            assert crawler.session is not None
