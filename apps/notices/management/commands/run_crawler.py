from django.core.management.base import BaseCommand
from services.crawler_service import CrawlerService
import logging

logger = logging.getLogger('crawlers')


class Command(BaseCommand):
    help = '모든 기관의 공고를 수집합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--agency',
            type=str,
            help='특정 기관만 크롤링 (예: rda)',
        )

    def handle(self, *args, **options):
        try:
            agency = options.get('agency')
            service = CrawlerService()
            
            if agency:
                self.stdout.write(f'크롤링 시작: {agency}')
                results = service.crawl_agency(agency)
            else:
                self.stdout.write('모든 기관 크롤링 시작...')
                results = service.crawl_all()
            
            self.stdout.write(
                self.style.SUCCESS(f'OK: 크롤링 완료 - {results}개의 공고 수집')
            )
        except Exception as e:
            logger.error(f'크롤링 실패: {str(e)}', exc_info=True)
            self.stdout.write(
                self.style.ERROR(f'ERROR: 크롤링 실패 - {str(e)}')
            )
