"""
Step 2: 데이터베이스 모델 실행 가이드

마이그레이션 및 테스트 실행 방법
"""

# ========== 마이그레이션 생성 및 실행 ==========

# 1. 마이그레이션 파일 생성
# python manage.py makemigrations

# 2. 마이그레이션 상태 확인
# python manage.py showmigrations

# 3. 마이그레이션 적용
# python manage.py migrate

# 4. 마이그레이션 취소 (필요시)
# python manage.py migrate notices 0001  # 특정 마이그레이션으로 되돌리기


# ========== 슈퍼유저 생성 ==========

# python manage.py createsuperuser


# ========== 관리자 페이지 접속 ==========

# 개발: http://localhost:8000/admin
# Docker: http://localhost/admin


# ========== 기관 데이터 초기화 ==========

# 1. Django shell 실행
# python manage.py shell

# 2. 기관 생성
"""
from apps.notices.models import Agency

agencies = [
    {
        'code': 'rda',
        'name': '농촌진흥청',
        'name_en': 'Rural Development Administration',
        'website_url': 'https://www.rda.go.kr',
        'notice_url': 'https://www.rda.go.kr/home/cmsView.do?pageKey=notices',
        'crawler_method': 'api',
        'crawler_priority': 1,
    },
    {
        'code': 'koat',
        'name': 'KOAT(농업기술실용화재단)',
        'name_en': 'Korea Agro-Technology Foundation',
        'website_url': 'https://www.koat.or.kr',
        'crawler_method': 'html',
        'crawler_priority': 2,
    },
    {
        'code': 'smartfarm',
        'name': '스마트팜코리아',
        'name_en': 'SmartFarm Korea',
        'website_url': 'https://www.smartfarmkorea.net',
        'crawler_method': 'rss',
        'crawler_priority': 3,
    },
    {
        'code': 'startup',
        'name': '창업진흥원',
        'name_en': 'Korea Startup Center',
        'website_url': 'https://www.kstartup.or.kr',
        'crawler_method': 'html',
        'crawler_priority': 4,
    },
    {
        'code': 'bizinfo',
        'name': '기업마당',
        'name_en': 'Business Information Service',
        'website_url': 'https://www.bizinfo.go.kr',
        'api_url': 'https://api.bizinfo.go.kr',
        'crawler_method': 'api',
        'crawler_priority': 5,
    },
    # ... 더 많은 기관 추가
]

for agency_data in agencies:
    Agency.objects.get_or_create(code=agency_data['code'], defaults=agency_data)
"""


# ========== 테스트 실행 ==========

# 모든 테스트 실행
# pytest

# 특정 테스트만 실행
# pytest tests/test_models.py::TestNoticeModel::test_create_notice -v

# 커버리지 리포트 생성
# pytest --cov=apps/notices --cov-report=html

# 종료후: htmlcov/index.html 파일 열기


# ========== 데이터베이스 상태 확인 ==========

# 스키마 확인
# python manage.py inspectdb

# SQL 확인
# python manage.py sqlmigrate notices 0001

# 테이블 목록
# python manage.py dbshell
# \dt  (PostgreSQL)


# ========== 캐시 초기화 (필요시) ==========

# python manage.py shell
# from django.core.cache import cache
# cache.clear()


# ========== 다음 단계 ==========

# Step 3: BaseCrawler 설계
# - crawlers/base.py 구현
# - 기본 크롤러 추상 클래스
# - 오류 처리 및 재시도 로직
