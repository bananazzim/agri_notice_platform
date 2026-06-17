"""
유틸리티 함수

크롤러 및 시스템에서 사용하는 공통 유틸리티
"""
import re
from datetime import datetime, timedelta
from typing import Optional, List
from urllib.parse import urljoin, urlparse
import time
from functools import wraps

from .logger import crawler_logger
from .exceptions import CrawlerConnectionError


def normalize_url(url: str, base_url: Optional[str] = None) -> str:
    """
    URL 정규화
    
    상대 URL을 절대 URL로 변환하고 정규화
    
    Args:
        url: 정규화할 URL
        base_url: 베이스 URL (상대 URL의 경우)
    
    Returns:
        정규화된 URL
    """
    if not url:
        return ""
    
    # 상대 URL을 절대 URL로 변환
    if base_url and not url.startswith('http'):
        url = urljoin(base_url, url)
    
    # URL 파싱
    parsed = urlparse(url)
    
    # 스킴이 없는 경우 https 추가
    if not parsed.scheme:
        url = 'https://' + url
    
    # 쿼리 파라미터 정렬 (동일 URL의 변형 제거)
    if parsed.query:
        from urllib.parse import parse_qs, urlencode
        params = parse_qs(parsed.query, keep_blank_values=True)
        sorted_params = sorted(params.items())
        sorted_query = urlencode(sorted_params, doseq=True)
        url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{sorted_query}"
    
    return url.strip()


def normalize_date(date_str: str, formats: Optional[List[str]] = None) -> Optional[str]:
    """
    날짜 정규화
    
    다양한 형식의 날짜를 YYYY-MM-DD 형식으로 통일
    
    Args:
        date_str: 날짜 문자열
        formats: 시도할 날짜 형식 리스트
    
    Returns:
        정규화된 날짜 (YYYY-MM-DD) 또는 None
    """
    if not date_str:
        return None
    
    date_str = str(date_str).strip()
    
    # 기본 형식들
    if formats is None:
        formats = [
            '%Y-%m-%d',           # 2024-06-15
            '%Y/%m/%d',           # 2024/06/15
            '%Y.%m.%d',           # 2024.06.15
            '%Y년 %m월 %d일',    # 2024년 06월 15일
            '%y-%m-%d',           # 24-06-15
            '%m-%d-%Y',           # 06-15-2024
            '%m/%d/%Y',           # 06/15/2024
            '%d-%m-%Y',           # 15-06-2024
            '%Y%m%d',             # 20240615
        ]
    
    for fmt in formats:
        try:
            date_obj = datetime.strptime(date_str, fmt)
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    # 정규표현식으로 YYYY-MM-DD 패턴 찾기
    match = re.search(r'(\d{4})[.\-/]?(\d{1,2})[.\-/]?(\d{1,2})', date_str)
    if match:
        year, month, day = match.groups()
        try:
            date_obj = datetime(int(year), int(month), int(day))
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            pass
    
    return None


def clean_text(text: str) -> str:
    """
    텍스트 정제
    
    여러 줄 공백, 특수 문자 등을 제거하고 정리
    
    Args:
        text: 정제할 텍스트
    
    Returns:
        정제된 텍스트
    """
    if not text:
        return ""
    
    # 여러 줄 공백을 단일 공백으로
    text = re.sub(r'\s+', ' ', text)
    
    # 앞뒤 공백 제거
    text = text.strip()
    
    return text


def extract_domain(url: str) -> str:
    """
    URL에서 도메인 추출
    
    Args:
        url: URL
    
    Returns:
        도메인 (예: example.com)
    """
    parsed = urlparse(url)
    domain = parsed.netloc
    
    # www. 제거
    if domain.startswith('www.'):
        domain = domain[4:]
    
    return domain


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """
    재시도 데코레이터 (Exponential Backoff)
    
    함수 실행 실패 시 지정된 횟수까지 재시도
    
    Args:
        max_retries: 최대 재시도 횟수
        base_delay: 기본 대기 시간 (초)
        exponential_base: 지수 베이스 (매 재시도마다 곱해짐)
        exceptions: 재시도할 예외 타입
    
    Usage:
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        def fetch_data():
            # 실행 코드
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        delay = base_delay * (exponential_base ** attempt)
                        crawler_logger.warning(
                            f"{func.__name__} 재시도 {attempt + 1}/{max_retries} "
                            f"({delay}초 후): {str(e)}"
                        )
                        time.sleep(delay)
                    else:
                        crawler_logger.error(
                            f"{func.__name__} 최대 재시도 횟수 초과: {str(e)}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


def calculate_days_to_deadline(deadline_str: Optional[str]) -> Optional[int]:
    """
    마감까지 남은 일수 계산
    
    Args:
        deadline_str: 마감일 (YYYY-MM-DD 형식)
    
    Returns:
        남은 일수 (None이면 마감일 없음)
    """
    if not deadline_str:
        return None
    
    try:
        deadline_date = datetime.strptime(deadline_str, '%Y-%m-%d').date()
        today = datetime.now().date()
        return (deadline_date - today).days
    except (ValueError, AttributeError):
        return None


def is_deadline_soon(
    deadline_str: Optional[str],
    days_threshold: int = 7
) -> bool:
    """
    마감 임박 여부 확인
    
    Args:
        deadline_str: 마감일
        days_threshold: 임박 기준 일수 (기본: 7일)
    
    Returns:
        True if 마감 임박, False otherwise
    """
    days_left = calculate_days_to_deadline(deadline_str)
    
    if days_left is None:
        return False
    
    return 0 <= days_left <= days_threshold


def estimate_reading_time(text: str) -> int:
    """
    텍스트 읽기 시간 추정 (분)
    
    평균 읽기 속도: 분당 200-250 단어
    
    Args:
        text: 텍스트
    
    Returns:
        읽기 시간 (분)
    """
    if not text:
        return 0
    
    word_count = len(text.split())
    reading_speed = 200  # 분당 단어 수
    
    return max(1, word_count // reading_speed)
