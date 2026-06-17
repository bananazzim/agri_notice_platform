"""
크롤러 레지스트리

모든 기관별 크롤러를 등록하고 관리
"""
from typing import Dict, Type, Optional, List
from core.logger import crawler_logger
from .base import BaseCrawler


class CrawlerRegistry:
    """
    크롤러 레지스트리
    
    모든 기관별 크롤러를 등록하고 조회하는 중앙 관리 시스템
    """
    
    _crawlers: Dict[str, Type[BaseCrawler]] = {}
    
    @classmethod
    def register(cls, agency_code: str, crawler_class: Type[BaseCrawler]):
        """
        크롤러 등록
        
        Args:
            agency_code: 기관 코드 (예: rda)
            crawler_class: 크롤러 클래스
        """
        if not issubclass(crawler_class, BaseCrawler):
            raise TypeError(
                f"{crawler_class}는 BaseCrawler의 서브클래스여야 합니다"
            )
        
        cls._crawlers[agency_code] = crawler_class
        crawler_logger.debug(f"✓ 크롤러 등록: {agency_code}")
    
    @classmethod
    def get(cls, agency_code: str) -> Optional[BaseCrawler]:
        """
        크롤러 인스턴스 조회
        
        Args:
            agency_code: 기관 코드
        
        Returns:
            크롤러 인스턴스 또는 None
        """
        crawler_class = cls._crawlers.get(agency_code)
        
        if not crawler_class:
            crawler_logger.warning(f"⚠️  등록되지 않은 크롤러: {agency_code}")
            return None
        
        return crawler_class()
    
    @classmethod
    def get_all(cls) -> Dict[str, BaseCrawler]:
        """
        모든 크롤러 인스턴스 조회
        
        Returns:
            크롤러 딕셔너리 {code: instance}
        """
        return {code: crawler_class() for code, crawler_class in cls._crawlers.items()}
    
    @classmethod
    def get_codes(cls) -> List[str]:
        """
        등록된 모든 기관 코드 조회
        
        Returns:
            기관 코드 리스트
        """
        return list(cls._crawlers.keys())
    
    @classmethod
    def is_registered(cls, agency_code: str) -> bool:
        """
        크롤러 등록 여부 확인
        
        Args:
            agency_code: 기관 코드
        
        Returns:
            등록된 경우 True
        """
        return agency_code in cls._crawlers
    
    @classmethod
    def list_crawlers(cls) -> Dict[str, str]:
        """
        등록된 크롤러 목록 조회
        
        Returns:
            {코드: 기관명} 딕셔너리
        """
        crawlers = {}
        for code, crawler_class in cls._crawlers.items():
            instance = crawler_class()
            crawlers[code] = instance.agency_name
        return crawlers


# ========== 데코레이터 기반 등록 ==========

def register_crawler(agency_code: str):
    """
    크롤러 등록 데코레이터
    
    Usage:
        @register_crawler('rda')
        class RDACrawler(BaseCrawler):
            ...
    """
    def decorator(crawler_class: Type[BaseCrawler]):
        CrawlerRegistry.register(agency_code, crawler_class)
        return crawler_class
    return decorator


# ========== 동적 크롤러 로딩 ==========

def auto_register_crawlers():
    """
    agencies 디렉토리의 모든 크롤러 자동 등록
    
    각 크롤러 파일에서 @register_crawler 데코레이터를 사용해야 함
    """
    import os
    import importlib
    from pathlib import Path
    
    crawlers_dir = Path(__file__).parent / 'agencies'
    
    for file_path in crawlers_dir.glob('*.py'):
        if file_path.name.startswith('_'):
            continue
        
        module_name = file_path.stem
        try:
            module = importlib.import_module(f'crawlers.agencies.{module_name}')
            crawler_logger.debug(f"✓ 모듈 로드: crawlers.agencies.{module_name}")
        except ImportError as e:
            crawler_logger.warning(
                f"⚠️  모듈 로드 실패: {module_name} - {str(e)}"
            )
        except Exception as e:
            crawler_logger.error(
                f"❌ 예상 외 오류: {module_name} - {str(e)}"
            )


# 앱 시작 시 크롤러 자동 등록
try:
    auto_register_crawlers()
except Exception as e:
    crawler_logger.warning(f"크롤러 자동 등록 실패: {str(e)}")
