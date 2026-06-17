"""
커스텀 예외 클래스

크롤러 및 시스템에서 발생하는 예외를 체계적으로 관리
"""


class CrawlerException(Exception):
    """크롤러 기본 예외"""
    pass


class CrawlerConnectionError(CrawlerException):
    """크롤러 연결 실패 예외
    
    네트워크 오류, 타임아웃 등
    """
    pass


class CrawlerParseError(CrawlerException):
    """크롤러 파싱 실패 예외
    
    HTML 파싱, JSON 파싱 등 데이터 추출 실패
    """
    pass


class CrawlerAuthError(CrawlerException):
    """크롤러 인증 실패 예외
    
    API 키 오류, 로그인 실패 등
    """
    pass


class CrawlerNotImplementedError(CrawlerException):
    """크롤러 메서드 미구현 예외"""
    pass


class DuplicateNoticeError(CrawlerException):
    """중복 공고 예외
    
    이미 저장된 공고를 감지했을 때 발생
    """
    pass


class AIAnalysisError(Exception):
    """AI 분석 오류 예외"""
    pass
