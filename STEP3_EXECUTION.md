"""
Step 3: BaseCrawler 설계 실행 가이드

크롤러 기본 클래스 및 유틸리티 테스트
"""

# ========== 파일 구조 ==========

# crawlers/
# ├── __init__.py
# ├── base.py                    # BaseCrawler 추상 클래스 (400+ 줄)
# ├── registry.py                # 크롤러 레지스트리 (100+ 줄)
# └── agencies/                  # 기관별 크롤러 (Step 4)
#     └── __init__.py
#
# core/
# ├── __init__.py
# ├── exceptions.py              # 커스텀 예외 (7개)
# ├── logger.py                  # 로깅 설정
# └── utils.py                   # 유틸리티 함수 (200+ 줄)
#
# tests/
# ├── __init__.py
# ├── conftest.py
# ├── test_models.py            # Step 2 모델 테스트
# └── test_crawlers.py          # BaseCrawler 테스트 (350+ 줄)


# ========== 테스트 실행 ==========

# 모든 크롤러 테스트 실행
# pytest tests/test_crawlers.py -v

# 특정 테스트만 실행
# pytest tests/test_crawlers.py::TestBaseCrawler::test_normalize_url -v

# 커버리지 포함
# pytest tests/test_crawlers.py --cov=crawlers --cov=core --cov-report=html

# 결과 확인
# htmlcov/index.html


# ========== BaseCrawler 사용 예제 ==========

# Django Shell에서 테스트
# python manage.py shell

"""
from crawlers.base import BaseCrawler
from crawlers.registry import CrawlerRegistry, register_crawler

# 1. BaseCrawler를 상속하는 커스텀 크롤러 작성
@register_crawler('custom')
class CustomCrawler(BaseCrawler):
    agency_name = "Custom Agency"
    agency_code = "custom"
    website_url = "https://custom.go.kr"
    crawler_method = "html"
    
    def fetch_notices(self):
        # 크롤링 로직 구현
        notices = []
        
        # 예: 웹 페이지에서 공고 추출
        response = self.fetch_page('https://custom.go.kr/notices')
        soup = self.parse_html(response.text)
        
        for item in soup.select('.notice-item'):
            notice = {
                'title': item.select_one('.title').text,
                'url': item.select_one('a')['href'],
                'posted_date': item.select_one('.date').text,
                'content': item.select_one('.content').text,
            }
            notices.append(notice)
        
        return notices

# 2. 크롤러 실행
crawler = CrawlerRegistry.get('custom')
result = crawler.crawl()

# 3. 결과 확인
print(f"상태: {result['status']}")
print(f"수집: {result['count']}개")
print(f"소요시간: {result['duration']:.2f}초")

# 4. 공고 정보 확인
for notice in result['notices']:
    print(f"- {notice['title']}")
    print(f"  URL: {notice['url']}")
    print(f"  게시일: {notice['posted_date']}")
"""


# ========== 유틸리티 함수 사용 ==========

# URL 정규화
# from core.utils import normalize_url
# url = normalize_url('relative/path', 'https://example.com')

# 날짜 정규화
# from core.utils import normalize_date
# date = normalize_date('2024/06/15')  # '2024-06-15'

# 텍스트 정제
# from core.utils import clean_text
# text = clean_text('  테스트   문자열  ')  # '테스트 문자열'

# 마감 임박 확인
# from core.utils import is_deadline_soon
# if is_deadline_soon('2024-06-20', 7):  # 7일 이내
#     print("마감 임박!")

# 재시도 데코레이터 사용
"""
from core.utils import retry_with_backoff

@retry_with_backoff(max_retries=3, base_delay=1.0)
def fetch_data():
    # 실행 코드
    # 실패 시 자동으로 재시도됨
    pass
"""


# ========== 로깅 사용 ==========

# 크롤러 로거 사용
"""
from core.logger import get_crawler_logger

logger = get_crawler_logger('rda')
logger.info("크롤링 시작")
logger.debug("디버그 정보")
logger.warning("경고")
logger.error("에러")
"""


# ========== 예외 처리 ==========

"""
from core.exceptions import (
    CrawlerConnectionError,
    CrawlerParseError,
    CrawlerNotImplementedError,
)

try:
    crawler = SomeCrawler()
    result = crawler.crawl()
except CrawlerConnectionError as e:
    print(f"연결 실패: {e}")
except CrawlerParseError as e:
    print(f"파싱 실패: {e}")
"""


# ========== 다음 단계 ==========

# Step 4: 기관별 크롤러 구현
# - RDA (농촌진흥청) - API 기반
# - KOAT - HTML 크롤링
# - SmartFarm - RSS Feed
# - 창업진흥원 - HTML 크롤링
# - 기업마당 - Open API
# ... 등 11개 기관 크롤러 구현
