"""
API 크롤러 설정

RDA, 기업마당, MAFRA API 설정 및 상수
"""

from django.conf import settings

# ========== API 엔드포인트 ==========

# RDA (농촌진흥청) API
RDA_NOTICE_API = "https://www.rda.go.kr/api/notice/list"
RDA_NEWS_API = "https://www.rda.go.kr/api/news/list"
RDA_SUPPORT_API = "https://www.rda.go.kr/api/support/list"

# 기업마당 API
# 정부 공동 데이터포탈: https://www.data.go.kr/
BIZINFO_SUPPORT_API = "https://apis.data.go.kr/B090041/openapi/service/SBPMService/getList"

# MAFRA (농림축산식품부) API
MAFRA_RSS_URL = "https://www.mafra.go.kr/rss/newsList.xml"
MAFRA_API_BASE = "https://www.mafra.go.kr/api"

# ========== API 설정 ==========

API_CONFIGS = {
    'rda': {
        'name': '농촌진흥청',
        'base_url': 'https://www.rda.go.kr',
        'endpoints': {
            'support': RDA_SUPPORT_API,
            'news': RDA_NEWS_API,
        },
        'timeout': 30,
        'retry_count': 3,
        'rate_limit': 100,  # requests per hour
        'requires_auth': False,
    },
    'bizinfo': {
        'name': '기업마당',
        'base_url': 'https://www.bizinfo.go.kr',
        'api_endpoint': BIZINFO_SUPPORT_API,
        'timeout': 30,
        'retry_count': 3,
        'rate_limit': 100,
        'requires_auth': True,
        'auth_type': 'api_key',
        'api_key_env': 'BIZINFO_API_KEY',
    },
    'mafra': {
        'name': '농림축산식품부',
        'base_url': 'https://www.mafra.go.kr',
        'rss_url': MAFRA_RSS_URL,
        'timeout': 30,
        'retry_count': 3,
        'rate_limit': 100,
        'requires_auth': False,
        'hybrid': True,  # RSS + 웹 크롤링
    },
}

# ========== API 응답 형식 ==========

# RDA API 응답 예시
# {
#     "success": true,
#     "list": [
#         {
#             "id": "12345",
#             "title": "공고 제목",
#             "subject": "공고 주제",
#             "content": "공고 내용",
#             "body": "상세 내용",
#             "url": "https://...",
#             "link": "https://...",
#             "createdDate": "2024-06-15",
#             "date": "2024-06-15",
#             "deadline": "2024-07-15",
#             "endDate": "2024-07-15",
#             "category": "지원",
#             "summary": "요약",
#         }
#     ],
#     "totalPages": 5,
#     "currentPage": 1,
# }

# 기업마당 API 응답 예시 (XML)
# <?xml version="1.0" encoding="UTF-8"?>
# <root>
#     <item>
#         <bizTitle>기업 지원사업</bizTitle>
#         <bizSummary>요약</bizSummary>
#         <bizUrl>https://...</bizUrl>
#         <bizRegistDt>2024-06-15</bizRegistDt>
#         <bizDeadline>2024-07-15</bizDeadline>
#         <bizType>자금지원</bizType>
#     </item>
# </root>

# MAFRA RSS 응답 예시 (RSS XML)
# <?xml version="1.0" encoding="UTF-8"?>
# <rss version="2.0">
#     <channel>
#         <title>농림축산식품부 뉴스</title>
#         <item>
#             <title>공고 제목</title>
#             <link>https://...</link>
#             <description>공고 설명</description>
#             <pubDate>Mon, 15 Jun 2024 10:30:00 +0900</pubDate>
#         </item>
#     </channel>
# </rss>

# ========== 페이지네이션 설정 ==========

PAGINATION_CONFIGS = {
    'rda': {
        'page_param': 'page',
        'page_size_param': 'pageSize',
        'default_page_size': 50,
        'max_pages': 5,
    },
    'bizinfo': {
        'page_param': 'pageNo',
        'page_size_param': 'numOfRows',
        'default_page_size': 50,
        'max_pages': 3,
    },
    'mafra': {
        'type': 'rss',  # RSS는 기본 페이지네이션 없음
        'max_items': 100,
    },
}

# ========== 데이터 매핑 ==========

FIELD_MAPPING = {
    'rda': {
        'title': ['title', 'subject'],
        'content': ['content', 'body'],
        'url': ['url', 'link'],
        'posted_date': ['createdDate', 'date'],
        'deadline': ['deadline', 'endDate'],
        'category': ['category'],
        'summary': ['summary'],
    },
    'bizinfo': {
        'title': ['bizTitle', 'title'],
        'content': ['bizSummary', 'summary'],
        'url': ['bizUrl', 'link'],
        'posted_date': ['bizRegistDt', 'date'],
        'deadline': ['bizDeadline', 'endDate'],
        'category': ['bizType'],
    },
    'mafra': {
        'title': ['title'],
        'content': ['summary', 'description'],
        'url': ['link'],
        'posted_date': ['published', 'pubDate'],
    },
}

# ========== 카테고리 매핑 ==========

CATEGORY_KEYWORDS = {
    'support': ['지원', '사업', '모집', '신청', '자금', '투자'],
    'education': ['교육', '훈련', '과정', '프로그램', '학교'],
    'contest': ['공모', '경진', '대회', '공개모집', '공모전'],
    'rd': ['기술개발', 'r&d', 'rd', '연구', '개발'],
    'startup': ['창업', '스타트업', '시작'],
}

# ========== 환경 변수 ==========

def get_api_key(crawler_code: str) -> str:
    """
    API 키 조회
    
    Args:
        crawler_code: 크롤러 코드 (rda, bizinfo, mafra)
    
    Returns:
        API 키
    """
    config = API_CONFIGS.get(crawler_code, {})
    
    if config.get('requires_auth'):
        api_key_env = config.get('api_key_env')
        if api_key_env:
            import os
            return os.getenv(api_key_env)
    
    return None

# ========== 타임아웃 설정 ==========

TIMEOUT_CONFIG = {
    'rda': 30,
    'bizinfo': 30,
    'mafra': 30,
}

# ========== 재시도 설정 ==========

RETRY_CONFIG = {
    'max_retries': 3,
    'base_delay': 1.0,
    'exponential_base': 2.0,
    'backoff_max': 30.0,
}

# ========== Rate Limiting ==========

RATE_LIMIT_CONFIG = {
    'rda': {
        'requests_per_hour': 100,
        'burst_size': 10,
    },
    'bizinfo': {
        'requests_per_hour': 100,
        'burst_size': 10,
    },
    'mafra': {
        'requests_per_hour': 100,
        'burst_size': 10,
    },
}
