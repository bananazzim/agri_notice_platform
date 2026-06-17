"""
Step 4A: API 기반 크롤러 실행 가이드

RDA, 기업마당, MAFRA 크롤러 테스트 및 사용
"""

# ========== 파일 구조 ==========

# crawlers/
# ├── agencies/
# │   ├── __init__.py
# │   ├── rda.py                  # RDA (농촌진흥청) 크롤러
# │   ├── bizinfo.py              # 기업마당 크롤러
# │   ├── mafra.py                # MAFRA (농림축산식품부) 크롤러
# │   └── config.py               # API 설정
# │
# tests/
# └── test_api_crawlers.py        # API 크롤러 테스트


# ========== 설정 (환경 변수) ==========

# .env 파일에 다음 추가:

"""
# 기업마당 API 설정
BIZINFO_API_KEY=your_api_key_here

# RDA API 설정 (선택사항)
RDA_API_KEY=your_rda_api_key_here

# MAFRA RSS Feed URL (선택사항, 커스터마이징)
MAFRA_RSS_URL=https://www.mafra.go.kr/rss/newsList.xml
"""


# ========== 테스트 실행 ==========

# 모든 API 크롤러 테스트
# pytest tests/test_api_crawlers.py -v

# RDA 테스트만
# pytest tests/test_api_crawlers.py::TestRDACrawler -v

# 기업마당 테스트만
# pytest tests/test_api_crawlers.py::TestBizinfoCrawler -v

# MAFRA 테스트만
# pytest tests/test_api_crawlers.py::TestMAFRACrawler -v

# 커버리지 포함
# pytest tests/test_api_crawlers.py --cov=crawlers.agencies --cov-report=html


# ========== Django Shell에서 테스트 ==========

# python manage.py shell

"""
from crawlers.registry import CrawlerRegistry

# 1. 등록된 크롤러 확인
print(CrawlerRegistry.list_crawlers())

# 2. RDA 크롤러 테스트
rda_crawler = CrawlerRegistry.get('rda')
result = rda_crawler.crawl()
print(f"상태: {result['status']}")
print(f"수집: {result['count']}개")

# 3. 기업마당 크롤러 테스트 (API 키 필요)
bizinfo_crawler = CrawlerRegistry.get('bizinfo')
result = bizinfo_crawler.crawl()
print(f"기업마당: {result['count']}개")

# 4. MAFRA 크롤러 테스트
mafra_crawler = CrawlerRegistry.get('mafra')
result = mafra_crawler.crawl()
print(f"MAFRA: {result['count']}개")

# 5. 크롤러 결과 보기
for notice in result['notices'][:3]:
    print(f"- {notice['title']}")
    print(f"  URL: {notice['url']}")
    print(f"  카테고리: {notice['category']}")
"""


# ========== 개별 크롤러 사용 예제 ==========

# RDA 크롤러 사용
"""
from crawlers.agencies.rda import RDACrawler

crawler = RDACrawler()
result = crawler.crawl()

print(f"수집 상태: {result['status']}")
print(f"총 공고: {result['count']}개")
print(f"소요시간: {result['duration']:.2f}초")

if result['status'] == 'success':
    for notice in result['notices'][:5]:
        print(f"- {notice['title']}")
        print(f"  마감: {notice['deadline']}")
        print(f"  카테고리: {notice['category']}")
"""

# 기업마당 크롤러 사용
"""
from crawlers.agencies.bizinfo import BizinfoCrawler

crawler = BizinfoCrawler()
result = crawler.crawl()

print(f"수집 상태: {result['status']}")
print(f"총 공고: {result['count']}개")

# API가 없으면 웹 크롤링만 수행됨
# API 키를 설정하면: .env 파일에서 로드
"""

# MAFRA 크롤러 사용
"""
from crawlers.agencies.mafra import MAFRACrawler

crawler = MAFRACrawler()
result = crawler.crawl()

print(f"수집 상태: {result['status']}")
print(f"총 공고: {result['count']}개")

# RSS Feed + 웹 크롤링 하이브리드 방식
# RSS에서는 최신 공고만 추출, 웹에서 추가 공고 수집
"""


# ========== 크롤러 결과 저장 (DB) ==========

# 크롤링 결과를 데이터베이스에 저장하는 예제는 Step 5에서 구현합니다.

"""
from apps.notices.models import Notice, CrawlerLog
from crawlers.agencies.rda import RDACrawler
from django.utils import timezone

crawler = RDACrawler()
result = crawler.crawl()

# 크롤링 로그 저장
log = CrawlerLog.objects.create(
    agency_id='rda',
    status=result['status'],
    notices_collected=result['count'],
    notices_saved=0,  # Step 5에서 계산
    error_message=result.get('error'),
)

# 공고 저장 (중복 제거)
for notice_data in result['notices']:
    notice, created = Notice.objects.get_or_create(
        url=notice_data['url'],
        defaults={
            'agency_id': 'rda',
            'title': notice_data['title'],
            'content': notice_data['content'],
            'posted_date': notice_data['posted_date'],
            'deadline': notice_data['deadline'],
            'category': notice_data['category'],
        }
    )
    if created:
        log.notices_saved += 1

log.save()
"""


# ========== API 설정 및 주의사항 ==========

# 1. RDA (농촌진흥청)
#    - 공개 API (별도 인증 불필요)
#    - 요청 제한: 약간의 Rate Limiting 있음 (자세한 내용은 공식 문서 참고)
#    - 응답 형식: JSON
#    - 지원: 최신 공고, 지원사업, 뉴스

# 2. 기업마당 (정부 공동 데이터포탈)
#    - API 키 필요 (https://www.data.go.kr에서 신청)
#    - 응답 형식: XML
#    - 웹 크롤링 보완: API의 한계를 보충하기 위해 웹에서도 수집

# 3. MAFRA (농림축산식품부)
#    - RSS Feed 공개 (별도 인증 불필요)
#    - 응답 형식: RSS XML
#    - 웹 크롤링: RSS Feed 외의 공고를 보충
#    - 하이브리드 방식: RSS + 웹 크롤링

# ========== 성능 최적화 ==========

# 1. 재시도 로직
#    - 자동 3회 재시도 (지수 백오프)
#    - 1초 → 2초 → 4초

# 2. User-Agent 로테이션
#    - 4개의 User-Agent 자동 로테이션
#    - IP 차단 회피

# 3. 캐싱 (Step 5에서)
#    - 최근 공고 Redis 캐싱
#    - 캐시 TTL: 3600초 (1시간)

# ========== 에러 처리 ==========

# 예상되는 에러:
# - CrawlerConnectionError: 네트워크 연결 실패
# - CrawlerParseError: 응답 파싱 실패
# - DuplicateNoticeError: 중복 공고 (Step 5)

# ========== 로깅 ==========

# 크롤러별 로그:
# logs/crawler.log  - 전체 크롤러 로그
# logs/scheduler.log - 스케줄러 로그 (Step 6)
# logs/ai.log - AI 분석 로그 (Step 7)

# 로그 확인 방법:
"""
tail -f logs/crawler.log
"""

# ========== 다음 단계 ==========

# Step 4B: RSS Feed 크롤러 구현
# - SmartFarm Korea
# - NIPA
# - 한국농업기술진흥원 (KOAT)

# Step 4C: HTML 크롤링 크롤러 구현
# - 창업진흥원
# - 테크노파크 등

# Step 5: 크롤러 서비스 (CrawlerService)
# - 크롤러 결과 통합
# - 중복 제거
# - 데이터베이스 저장
