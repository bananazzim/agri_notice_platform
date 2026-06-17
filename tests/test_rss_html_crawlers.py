"""
RSS 및 HTML 크롤러 테스트
"""
import pytest
from unittest.mock import Mock, patch

from crawlers.agencies.smartfarm import SmartFarmCrawler
from crawlers.agencies.nipa import NIPACrawler
from crawlers.agencies.koat import KOATCrawler
from crawlers.agencies.startup import StartupCrawler
from crawlers.agencies.jbtp import JBTPCrawler
from crawlers.agencies.gjtp import GJTPCrawler
from crawlers.agencies.smb import SMBCrawler
from crawlers.agencies.common import dedupe_notices, extract_deadline_from_text
from crawlers.registry import CrawlerRegistry


def test_extract_deadline_from_application_period_text():
    text = "신청기간 2026.06.17 ~ 2026.06.24 18:00까지 온라인 접수"

    assert extract_deadline_from_text(text) == "2026-06-24"


def test_extract_deadline_from_deadline_label_text():
    text = "접수마감: 2026년 7월 3일 금요일 17시"

    assert extract_deadline_from_text(text) == "2026-07-03"


def test_extract_deadline_from_period_with_yearless_end_date():
    text = "ㅇ ( 접수기간 ) 2026. 4. 1.(수) ~ 4. 30.(목)"

    assert extract_deadline_from_text(text) == "2026-04-30"


def test_extract_deadline_from_participation_receipt_text():
    text = "참가 접수: 2026년 5월 26일(화) 10:00 ~ 7월 3일(금) 18:00 까지"

    assert extract_deadline_from_text(text) == "2026-07-03"


def test_extract_deadline_from_koat_receipt_period_text():
    text = "- 접수기간: 2026. 6. 1.(월) ~ 6. 29.(월) 10:00 까지"

    assert extract_deadline_from_text(text) == "2026-06-29"


def test_dedupe_notices_merges_detail_deadline_for_same_url():
    notices = dedupe_notices(
        [
            {
                "agency": "koat",
                "title": "2026 스마트농업 AI 경진대회 참가 모집",
                "url": "https://www.koat.or.kr/board/business/16275/view.do",
                "posted_date": "2026-06-01",
                "deadline": None,
                "category": "contest",
                "summary": "",
                "content": "",
            },
            {
                "agency": "koat",
                "title": "2026 스마트농업 AI 경진대회 참가 모집",
                "url": "https://www.koat.or.kr/board/business/16275/view.do",
                "posted_date": "2026-06-01",
                "deadline": "2026-06-29",
                "category": "contest",
                "summary": "접수기간: 2026. 6. 1.(월) ~ 6. 29.(월) 10:00 까지",
                "content": "2026 스마트농업 AI 경진대회 참가 모집 접수기간: 2026. 6. 1.(월) ~ 6. 29.(월) 10:00 까지",
            },
        ]
    )

    assert len(notices) == 1
    assert notices[0]["deadline"] == "2026-06-29"
    assert "접수기간" in notices[0]["content"]


class TestSmartFarmCrawler:
    @pytest.fixture
    def crawler(self):
        return SmartFarmCrawler()

    def test_registration(self, crawler):
        assert CrawlerRegistry.is_registered('smartfarm')
        assert isinstance(CrawlerRegistry.get('smartfarm'), SmartFarmCrawler)

    @patch('crawlers.base.BaseCrawler.parse_rss')
    def test_fetch_notices(self, mock_parse_rss, crawler):
        mock_feed = Mock()
        mock_feed.entries = [
            {
                'title': '스마트팜 지원사업 공고',
                'link': 'https://smartfarm.go.kr/notice/1',
                'summary': '요약 내용',
                'published': 'Mon, 15 Jun 2024 10:30:00 +0900',
            }
        ]
        mock_parse_rss.return_value = mock_feed

        with patch.object(crawler, 'fetch_from_html', return_value=[]):
            notices = crawler.fetch_notices()
        assert len(notices) == 1
        assert notices[0]['category'] == 'support'
        assert notices[0]['posted_date'] == '2024-06-15'


class TestNIPACrawler:
    @pytest.fixture
    def crawler(self):
        return NIPACrawler()

    def test_registration(self, crawler):
        assert CrawlerRegistry.is_registered('nipa')
        assert isinstance(CrawlerRegistry.get('nipa'), NIPACrawler)

    @patch('crawlers.base.BaseCrawler.parse_rss')
    def test_fetch_notices(self, mock_parse_rss, crawler):
        mock_feed = Mock()
        mock_feed.entries = [
            {
                'title': 'NIPA 교육 프로그램',
                'link': 'https://nipa.kr/notice/1',
                'description': '교육 내용',
                'published': '2024-06-15T10:30:00Z',
            }
        ]
        mock_parse_rss.return_value = mock_feed

        notices = crawler.fetch_notices()
        assert len(notices) == 1
        assert notices[0]['category'] == 'education'
        assert notices[0]['posted_date'] == '2024-06-15'


class TestKOATCrawler:
    @pytest.fixture
    def crawler(self):
        return KOATCrawler()

    def test_registration(self, crawler):
        assert CrawlerRegistry.is_registered('koat')
        assert isinstance(CrawlerRegistry.get('koat'), KOATCrawler)

    @patch('crawlers.base.BaseCrawler.parse_rss')
    def test_fetch_notices(self, mock_parse_rss, crawler):
        mock_feed = Mock()
        mock_feed.entries = [
            {
                'title': 'KOAT 기술 연구 지원',
                'link': 'https://koat.or.kr/notice/1',
                'description': '연구 지원 내용',
                'published': 'Mon, 15 Jun 2024 10:30:00 +0900',
            }
        ]
        mock_parse_rss.return_value = mock_feed

        with patch.object(crawler, 'fetch_from_html', return_value=[]):
            notices = crawler.fetch_notices()
        assert len(notices) == 1
        assert notices[0]['category'] == 'rd'
        assert notices[0]['posted_date'] == '2024-06-15'


class TestStartupCrawler:
    @pytest.fixture
    def crawler(self):
        return StartupCrawler()

    def test_registration(self, crawler):
        assert CrawlerRegistry.is_registered('startup')
        assert isinstance(CrawlerRegistry.get('startup'), StartupCrawler)

    def test_parse_api_item(self, crawler):
        notice = crawler._parse_api_item(
            {
                'pbanc_sn': 178152,
                'biz_pbanc_nm': 'NextRise 2026, Seoul',
                'pbanc_ctnt': '창업가 및 예비 창업가들의 많은 참여바랍니다.',
                'supt_biz_clsfc': '행사ㆍ네트워크',
                'pbanc_rcpt_bgng_dt': '20260616',
                'pbanc_rcpt_end_dt': '20260619',
            }
        )

        assert notice is not None
        assert notice['title'] == 'NextRise 2026, Seoul'
        assert notice['posted_date'] == '2026-06-16'
        assert notice['deadline'] == '2026-06-19'
        assert notice['url'].endswith('pbancSn=178152')

    @patch('crawlers.agencies.startup.StartupCrawler.render_js_page')
    def test_fetch_notices(self, mock_render, crawler):
        html = (
            '<ul class="notice-list">'
            '<li><a href="/notice/1">창업지원 공고</a><span class="date">2024-06-15</span></li>'
            '</ul>'
        )
        mock_render.return_value = html

        with patch.object(crawler, 'fetch_from_api', return_value=[]), patch.object(
            crawler,
            '_fetch_from_static_html',
            return_value=[],
        ):
            notices = crawler.fetch_notices()
        assert len(notices) == 1
        assert notices[0]['title'] == '창업지원 공고'
        assert notices[0]['url'] == 'https://www.k-startup.go.kr/notice/1'


class TestJBTPCrawler:
    @pytest.fixture
    def crawler(self):
        return JBTPCrawler()

    def test_registration(self, crawler):
        assert CrawlerRegistry.is_registered('jbtp')
        assert isinstance(CrawlerRegistry.get('jbtp'), JBTPCrawler)

    @patch('crawlers.agencies.jbtp.JBTPCrawler.fetch_page')
    def test_fetch_notices(self, mock_fetch_page, crawler):
        response = Mock()
        response.text = (
            '<ul class="board-list">'
            '<li><a href="/notice/1">JBTP 공고</a><span class="date">2024-06-15</span></li>'
            '</ul>'
        )
        detail_response = Mock()
        detail_response.text = (
            '<div class="board-view">'
            '<h1>JBTP 공고</h1>'
            '<p>접수기간 2026.06.17 ~ 2026.06.24 18:00까지</p>'
            '</div>'
        )
        mock_fetch_page.side_effect = [response, detail_response]

        notices = crawler.fetch_notices()
        assert len(notices) == 1
        assert notices[0]['url'] == 'https://rnd.jbtp.or.kr/notice/1'
        assert notices[0]['deadline'] == '2026-06-24'


class TestGJTPCrawler:
    @pytest.fixture
    def crawler(self):
        return GJTPCrawler()

    def test_registration(self, crawler):
        assert CrawlerRegistry.is_registered('gjtp')
        assert isinstance(CrawlerRegistry.get('gjtp'), GJTPCrawler)

    @patch('crawlers.agencies.gjtp.GJTPCrawler.fetch_page')
    def test_fetch_notices(self, mock_fetch_page, crawler):
        response = Mock()
        response.text = (
            '<ul class="board-list">'
            '<li><a href="/notice/1">GJTP 공고</a><span class="date">2024-06-15</span></li>'
            '</ul>'
        )
        mock_fetch_page.return_value = response

        notices = crawler.fetch_notices()
        assert len(notices) == 1
        assert notices[0]['url'] == 'https://www.gjtp.or.kr/notice/1'


class TestSMBCrawler:
    @pytest.fixture
    def crawler(self):
        return SMBCrawler()

    def test_registration(self, crawler):
        assert CrawlerRegistry.is_registered('smb')
        assert isinstance(CrawlerRegistry.get('smb'), SMBCrawler)

    @patch('crawlers.agencies.smb.SMBCrawler.fetch_page')
    def test_fetch_notices(self, mock_fetch_page, crawler):
        response = Mock()
        response.text = (
            '<ul class="board-list">'
            '<li><a href="/notice/1">SMB 공고</a><span class="date">2024-06-15</span></li>'
            '</ul>'
        )
        mock_fetch_page.return_value = response

        notices = crawler.fetch_notices()
        assert len(notices) == 1
        assert notices[0]['url'] == 'https://www.mss.go.kr/notice/1'
