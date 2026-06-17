"""
로깅 설정

크롤러, 스케줄러, Django 등 각 컴포넌트별 로깅 설정
"""
import logging
import logging.handlers
from pathlib import Path
from django.conf import settings


def setup_logger(name, log_file=None, level=logging.DEBUG):
    """
    커스텀 로거 설정
    
    Args:
        name: 로거 이름
        log_file: 로그 파일 경로 (None이면 콘솔만 사용)
        level: 로깅 레벨
    
    Returns:
        logger: 설정된 logger 객체
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 포맷터 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 (있는 경우)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10,
            encoding='utf-8',
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# 크롤러 로거
crawler_logger = setup_logger(
    'crawlers',
    log_file=str(settings.BASE_DIR / 'logs' / 'crawler.log'),
    level=logging.DEBUG,
)

# 스케줄러 로거
scheduler_logger = setup_logger(
    'scheduler',
    log_file=str(settings.BASE_DIR / 'logs' / 'scheduler.log'),
    level=logging.DEBUG,
)

# AI 분석 로거
ai_logger = setup_logger(
    'ai',
    log_file=str(settings.BASE_DIR / 'logs' / 'ai.log'),
    level=logging.DEBUG,
)

# 데이터베이스 로거
db_logger = setup_logger(
    'database',
    log_file=str(settings.BASE_DIR / 'logs' / 'database.log'),
    level=logging.INFO,
)


def get_crawler_logger(agency_code):
    """기관별 크롤러 로거 반환"""
    return logging.getLogger(f'crawlers.{agency_code}')
