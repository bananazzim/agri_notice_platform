"""
API 기반 크롤러 테스트

RDA, 기업마당, MAFRA 크롤러 테스트
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from crawlers.agencies.rda import RDACrawler
from crawlers.agencies.bizinfo import BizinfoCrawler
from crawlers.agencies.mafra import MAFRACrawler
from crawlers.registry import CrawlerRegistry
from core.exceptions import CrawlerParseError, CrawlerConnectionError


# ========== RDA 크롤러 테스트 ==========

class TestRDACrawler:
    """RDA 크롤러 테스트"""
    
    @pytest.fixture
    def crawler(self):
        """RDA 크롤러"""
        return RDACrawler()
    
    def test_crawler_initialization(self, crawler):
        """크롤러 초기화"""
        assert crawler.agency_code == "rda"
        assert crawler.agency_name == "농촌진흥청"
        assert crawler.crawler_method == "api"
    
    def test_crawler_registration(self):
        """크롤러 등록"""
        assert CrawlerRegistry.is_registered('rda')
        crawler = CrawlerRegistry.get('rda')
        assert isinstance(crawler, RDACrawler)
    
    def test_categorize_notice(self, crawler):
        """공고 카테고리 분류"""
        test_cases = [
            ("기술개발비 지원", "rd"),
            ("R&D 과제 공모", "rd"),
            ("농촌교육 프로그램", "education"),
            ("스마트팜 창업지원", "startup"),
            ("공모전 개최", "contest"),
            ("일반공고", "support"),
        ]
        
        for title, expected_category in test_cases:
            category = crawler._categorize_notice("", title)
            assert category == expected_category
    
    @patch('crawlers.base.requests.Session.get')
    def test_fetch_from_api(self, mock_get, crawler):
        """API 호출"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'success': True,
            'list': [
                {
                    'title': '테스트 공고',
                    'url': 'https://rda.go.kr/notice/1',
                    'createdDate': '2024-06-15',
                    'content': '테스트 내용',
                }
            ],
            'totalPages': 1,
        }
        mock_get.return_value = mock_response
        
        data = crawler._fetch_from_api(crawler.SUPPORT_ENDPOINT)
        assert data['success']
        assert len(data['list']) == 1
    
    def test_parse_api_notice(self, crawler):
        """API 항목 파싱"""
        item = {
            'title': '지원사업 공고',
            'url': 'https://rda.go.kr/notice/1',
            'createdDate': '2024-06-15',
            'deadline': '2024-07-15',
            'content': '공고 내용',
        }
        
        notice = crawler._parse_api_notice(item)
        
        assert notice['title'] == '지원사업 공고'
        assert notice['url'] == 'https://rda.go.kr/notice/1'
        assert notice['posted_date'] == '2024-06-15'
        assert notice['deadline'] == '2024-07-15'


# ========== 기업마당 크롤러 테스트 ==========

class TestBizinfoCrawler:
    """기업마당 크롤러 테스트"""
    
    @pytest.fixture
    def crawler(self):
        """기업마당 크롤러"""
        crawler = BizinfoCrawler()
        crawler.api_key = None  # 테스트용 API 키 제거
        return crawler
    
    def test_crawler_initialization(self, crawler):
        """크롤러 초기화"""
        assert crawler.agency_code == "bizinfo"
        assert crawler.agency_name == "기업마당"
        assert crawler.crawler_method == "api"
    
    def test_crawler_registration(self):
        """크롤러 등록"""
        assert CrawlerRegistry.is_registered('bizinfo')
        crawler = CrawlerRegistry.get('bizinfo')
        assert isinstance(crawler, BizinfoCrawler)
    
    def test_categorize_notice(self, crawler):
        """공고 카테고리 분류"""
        test_cases = [
            ("정부지원금 신청", "support"),
            ("투자유치정보", "support"),
            ("컨설팅 서비스", "support"),
            ("기업교육 프로그램", "education"),
        ]
        
        for notice_type, expected_category in test_cases:
            category = crawler._categorize_notice(notice_type)
            assert category == expected_category
    
    def test_parse_xml_response(self, crawler):
        """XML 응답 파싱"""
        xml_str = """<?xml version="1.0" encoding="UTF-8"?>
        <root>
            <item>
                <title>지원사업 1</title>
                <url>https://bizinfo.go.kr/1</url>
                <date>2024-06-15</date>
            </item>
            <item>
                <title>지원사업 2</title>
                <url>https://bizinfo.go.kr/2</url>
                <date>2024-06-14</date>
            </item>
        </root>
        """
        
        items = crawler._parse_xml_response(xml_str)
        assert len(items) == 2
        assert items[0]['title'] == '지원사업 1'
    
    def test_parse_api_item(self, crawler):
        """API 항목 파싱"""
        item = {
            'bizTitle': '기업 지원사업',
            'bizSummary': '요약',
            'bizUrl': 'https://bizinfo.go.kr/notice/1',
            'bizRegistDt': '2024-06-15',
            'bizDeadline': '2024-07-15',
            'bizType': '자금지원',
        }
        
        notice = crawler._parse_api_item(item)
        
        assert notice['title'] == '기업 지원사업'
        assert notice['url'] == 'https://bizinfo.go.kr/notice/1'
        assert notice['category'] == 'support'


# ========== MAFRA 크롤러 테스트 ==========

class TestMAFRACrawler:
    """MAFRA 크롤러 테스트"""
    
    @pytest.fixture
    def crawler(self):
        """MAFRA 크롤러"""
        return MAFRACrawler()
    
    def test_crawler_initialization(self, crawler):
        """크롤러 초기화"""
        assert crawler.agency_code == "mafra"
        assert crawler.agency_name == "농림축산식품부"
        assert crawler.crawler_method == "rss"
    
    def test_crawler_registration(self):
        """크롤러 등록"""
        assert CrawlerRegistry.is_registered('mafra')
        crawler = CrawlerRegistry.get('mafra')
        assert isinstance(crawler, MAFRACrawler)
    
    def test_categorize_notice(self, crawler):
        """공고 카테고리 분류"""
        test_cases = [
            ("지원사업 공모", "support"),
            ("농촌교육 프로그램", "education"),
            ("농업기술경진대회", "contest"),
            ("스마트팜 기술개발", "rd"),
            ("일반뉴스", "news"),
        ]
        
        for title, expected_category in test_cases:
            category = crawler._categorize_notice(title)
            assert category == expected_category
    
    def test_parse_rss_date(self, crawler):
        """RSS 날짜 파싱"""
        # RFC 2822 형식
        rfc_date = "Mon, 15 Jun 2024 10:30:00 +0900"
        result = crawler._parse_rss_date(rfc_date)
        assert result == "2024-06-15"
        
        # ISO 8601 형식
        iso_date = "2024-06-15T10:30:00Z"
        result = crawler._parse_rss_date(iso_date)
        assert result == "2024-06-15"
    
    @patch('crawlers.base.BaseCrawler.parse_rss')
    def test_parse_rss_feed(self, mock_parse_rss, crawler):
        """RSS Feed 파싱"""
        # Mock RSS Feed
        mock_feed = Mock()
        mock_feed.entries = [
            Mock(
                title='공고 1',
                summary='요약',
                link='https://mafra.go.kr/notice/1',
                published='Mon, 15 Jun 2024 10:30:00 +0900',
                description='공고 내용',
            ),
            Mock(
                title='공고 2',
                summary='요약2',
                link='https://mafra.go.kr/notice/2',
                published='Mon, 14 Jun 2024 10:30:00 +0900',
                description='공고 내용2',
            ),
        ]
        
        mock_parse_rss.return_value = mock_feed
        
        notices = crawler._parse_rss_feed()
        assert len(notices) == 2
        assert notices[0]['title'] == '공고 1'


# ========== API 크롤러 통합 테스트 ==========

class TestAPIFetchNotices:
    """API 크롤러 fetch_notices 통합 테스트"""
    
    @patch('crawlers.agencies.rda.RDACrawler._fetch_from_api')
    def test_rda_fetch_notices(self, mock_fetch, ):
        """RDA fetch_notices"""
        mock_fetch.return_value = {
            'list': [
                {
                    'title': '공고 1',
                    'url': 'https://rda.go.kr/1',
                    'createdDate': '2024-06-15',
                    'content': '내용 1',
                }
            ],
            'totalPages': 1,
        }
        
        crawler = RDACrawler()
        notices = crawler.fetch_notices()
        
        assert len(notices) > 0
        assert notices[0]['title'] == '공고 1'
    
    def test_mafra_crawl_method(self):
        """MAFRA crawl 메서드"""
        crawler = MAFRACrawler()
        
        # 실제 크롤링 없이 기본 구조만 테스트
        with patch.object(crawler, '_parse_rss_feed', return_value=[]):
            with patch.object(crawler, '_fetch_from_website', return_value=[]):
                notices = crawler.fetch_notices()
                assert isinstance(notices, list)
