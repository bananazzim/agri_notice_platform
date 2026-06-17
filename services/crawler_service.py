from datetime import date, datetime
from typing import Dict, Any, List, Optional

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

from crawlers.registry import CrawlerRegistry
from apps.notices.constants import EXCLUDED_NOTICE_CATEGORIES
from apps.notices.models import Agency, Notice, CrawlerLog, CrawlerStatus
from core.exceptions import CrawlerException
from core.logger import get_crawler_logger
from services.email_notification_service import EmailNotificationService
from services.scoring_service import calculate_rule_score


class CrawlerService:
    """크롤러 서비스

    크롤러 실행, 공고 저장, 중복 제거, 로그 기록, 통계 갱신을 담당합니다.
    """

    def __init__(self):
        self.logger = get_crawler_logger('crawler_service')

    def crawl_agency(self, agency_code: str) -> int:
        """특정 기관의 크롤링을 실행하고 저장된 공고 수를 반환합니다."""
        saved_count, saved_notices = self._crawl_agency_with_notices(agency_code)
        self._send_email_notifications(saved_notices)
        return saved_count

    def _crawl_agency_with_notices(self, agency_code: str) -> tuple[int, list[Notice]]:
        crawler = CrawlerRegistry.get(agency_code)
        if crawler is None:
            raise ValueError(f"등록되지 않은 기관 코드: {agency_code}")

        self.logger.info(f"크롤링 시작: {agency_code}")

        result = crawler.crawl()
        agency = self._get_or_create_agency(crawler)

        saved_count, duplicated_count, saved_notices = self._save_notices(agency, result.get('notices', []))
        self._create_crawler_log(agency, result, saved_count, duplicated_count)
        self._update_crawler_status(agency, result, saved_count)
        self._update_agency_summary(agency, result)

        self.logger.info(
            f"{agency_code} 크롤링 완료: 저장 {saved_count}개, 중복 {duplicated_count}개"
        )

        return saved_count, saved_notices

    def crawl_all(self) -> int:
        """등록된 모든 기관을 순차적으로 크롤링하고 저장된 공고 수를 반환합니다."""
        total_saved = 0
        saved_notices: list[Notice] = []
        for agency_code in CrawlerRegistry.get_codes():
            try:
                saved_count, agency_saved_notices = self._crawl_agency_with_notices(agency_code)
                total_saved += saved_count
                saved_notices.extend(agency_saved_notices)
            except Exception as exc:
                self.logger.error(
                    f"{agency_code} 크롤링 중 오류 발생: {str(exc)}",
                    exc_info=True,
                )
        self._send_email_notifications(saved_notices)
        return total_saved

    def _get_or_create_agency(self, crawler: Any) -> Agency:
        """Crawler 정보로 Agency 모델을 생성 또는 갱신합니다."""
        agency_defaults = {
            'name': getattr(crawler, 'agency_name', crawler.agency_code),
            'website_url': getattr(crawler, 'website_url', ''),
            'notice_url': getattr(crawler, 'notice_url', ''),
            'api_url': getattr(crawler, 'api_url', ''),
            'rss_url': getattr(crawler, 'rss_url', ''),
            'crawler_method': getattr(crawler, 'crawler_method', 'html'),
            'is_active': True,
        }

        agency, _ = Agency.objects.update_or_create(
            code=crawler.agency_code,
            defaults=agency_defaults,
        )
        return agency

    def _coerce_date(self, value: Any, *, default_today: bool = False) -> date | None:
        """Convert crawler date values to date objects before model validation."""
        if value in (None, ''):
            return timezone.localdate() if default_today else None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value

        parsed = parse_date(str(value).strip())
        if parsed is not None:
            return parsed

        return timezone.localdate() if default_today else None

    def _save_notices(
        self,
        agency: Agency,
        notices: List[Dict[str, Any]],
    ) -> tuple[int, int, list[Notice]]:
        """공고를 DB에 저장하고 중복 카운트를 반환합니다."""
        saved_count = 0
        duplicated_count = 0
        saved_notices: list[Notice] = []

        for notice_data in notices:
            try:
                category = str(notice_data.get('category') or 'other').strip()
                if category in EXCLUDED_NOTICE_CATEGORIES:
                    self.logger.info(
                        "Skipping excluded notice category=%s url=%s",
                        category,
                        notice_data.get('url'),
                    )
                    continue

                posted_date = self._coerce_date(
                    notice_data.get('posted_date'),
                    default_today=True,
                )
                deadline = self._coerce_date(notice_data.get('deadline'))
                scoring_data = {
                    **notice_data,
                    'category': category,
                    'posted_date': posted_date,
                    'deadline': deadline,
                }
                rule_score = calculate_rule_score(scoring_data, agency)
                ai_status = (
                    'pending'
                    if rule_score.score >= 70 and rule_score.smartfarm_related
                    else 'skipped'
                )

                with transaction.atomic():
                    notice = self._find_existing_notice(
                        agency=agency,
                        url=notice_data.get('url'),
                        title=notice_data.get('title', ''),
                        posted_date=posted_date,
                    )
                    created = False
                    if notice is None:
                        notice = Notice.objects.create(
                            agency=agency,
                            title=notice_data.get('title', ''),
                            url=notice_data.get('url'),
                            content=notice_data.get('content', ''),
                            summary=notice_data.get('summary', ''),
                            posted_date=posted_date,
                            deadline=deadline,
                            category=category,
                            rule_score=rule_score.score,
                            importance_score=rule_score.score,
                            score_source='rule',
                            ai_tags=notice_data.get('ai_tags', []),
                            recommended_for=notice_data.get('recommended_for', []),
                            ai_analysis_status=ai_status,
                            ai_analysis_error='',
                        )
                        created = True

                if created:
                    saved_count += 1
                    saved_notices.append(notice)
                else:
                    self._update_existing_notice(
                        notice,
                        agency=agency,
                        notice_data=notice_data,
                        category=category,
                        posted_date=posted_date,
                        deadline=deadline,
                    )
                    duplicated_count += 1
            except IntegrityError:
                duplicated_count += 1
            except Exception as exc:
                self.logger.warning(
                    f"공고 저장 실패: {notice_data.get('url')} - {str(exc)}"
                )

        return saved_count, duplicated_count, saved_notices

    def _send_email_notifications(self, notices: list[Notice]) -> None:
        if not notices:
            return

        try:
            result = EmailNotificationService().send_for_notices(notices)
            self.logger.info(
                "이메일 알림 완료: 매칭 %s건, 발송 %s건, 실패 %s건, 건너뜀 %s건",
                result.matched,
                result.sent,
                result.failed,
                result.skipped,
            )
        except Exception as exc:
            self.logger.error("이메일 알림 처리 실패: %s", exc, exc_info=True)

    def _find_existing_notice(
        self,
        *,
        agency: Agency,
        url: str | None,
        title: str,
        posted_date: date | None,
    ) -> Notice | None:
        if url:
            notice = Notice.objects.filter(url=url).first()
            if notice is not None:
                return notice

        if title and posted_date:
            return Notice.objects.filter(
                agency=agency,
                title=title,
                posted_date=posted_date,
                is_deleted=False,
            ).first()

        return None

    def _update_existing_notice(
        self,
        notice: Notice,
        *,
        agency: Agency,
        notice_data: Dict[str, Any],
        category: str,
        posted_date: date | None,
        deadline: date | None,
    ) -> bool:
        update_fields: list[str] = []

        if deadline and notice.deadline != deadline:
            notice.deadline = deadline
            update_fields.append('deadline')

        url = str(notice_data.get('url') or '').strip()
        if url and notice.url != url:
            notice.url = url
            update_fields.append('url')

        content = str(notice_data.get('content') or '').strip()
        if content and (
            not notice.content
            or self._is_better_content(content, notice.content, notice.title)
        ):
            notice.content = content
            update_fields.append('content')

        summary = str(notice_data.get('summary') or '').strip()
        if summary and (
            not notice.summary
            or self._is_better_content(summary, notice.summary, notice.title)
        ):
            notice.summary = summary
            update_fields.append('summary')

        if category and notice.category in {'other', 'support'} and category != notice.category:
            notice.category = category
            update_fields.append('category')

        if not update_fields:
            return False

        scoring_data = {
            **notice_data,
            'category': notice.category,
            'posted_date': posted_date or notice.posted_date,
            'deadline': notice.deadline,
        }
        rule_score = calculate_rule_score(scoring_data, agency)
        notice.rule_score = rule_score.score
        if notice.score_source != 'ai':
            notice.importance_score = rule_score.score
            notice.score_source = 'rule'
            notice.ai_analysis_status = (
                'pending'
                if rule_score.score >= 70 and rule_score.smartfarm_related
                else 'skipped'
            )
            update_fields.extend(['importance_score', 'score_source', 'ai_analysis_status'])

        update_fields.extend(['rule_score', 'is_deadline_soon', 'updated_at'])
        notice.save(update_fields=list(dict.fromkeys(update_fields)))
        return True

    def _is_better_content(self, candidate: str, current: str, title: str) -> bool:
        if not current:
            return True

        current_has_title = bool(title and title in current)
        candidate_has_title = bool(title and title in candidate)
        if candidate_has_title and not current_has_title:
            return True

        if current.startswith(('본문 바로가기', '메뉴 Home', '검색박스')):
            return True

        return len(candidate) > len(current) * 2 and candidate_has_title

    def _create_crawler_log(
        self,
        agency: Agency,
        result: Dict[str, Any],
        saved_count: int,
        duplicated_count: int,
    ) -> CrawlerLog:
        """크롤링 실행 로그를 기록합니다."""
        return CrawlerLog.objects.create(
            agency=agency,
            status=result.get('status', 'failed'),
            notices_collected=result.get('count', 0),
            notices_saved=saved_count,
            notices_duplicated=duplicated_count,
            error_message=result.get('error', '') or '',
            start_time=result.get('start_time', timezone.now()),
            end_time=result.get('end_time', timezone.now()),
        )

    def _update_crawler_status(
        self,
        agency: Agency,
        result: Dict[str, Any],
        saved_count: int,
    ) -> CrawlerStatus:
        """기관별 누적 크롤링 통계를 갱신합니다."""
        status, _ = CrawlerStatus.objects.get_or_create(agency=agency)

        status.total_crawls += 1
        status.total_notices_collected += result.get('count', 0)
        status.total_notices_saved += saved_count

        if result.get('status') == 'success':
            status.successful_crawls += 1
        elif result.get('status') == 'partial':
            status.partial_crawls += 1
        else:
            status.failed_crawls += 1

        total_time = status.average_crawl_time * (status.total_crawls - 1)
        duration = result.get('duration', 0) or 0
        status.average_crawl_time = (
            (total_time + duration) / status.total_crawls
            if status.total_crawls > 0 else 0
        )
        status.last_status = result.get('status', '')
        status.last_crawled_at = timezone.now()
        status.save()

        return status

    def _update_agency_summary(
        self,
        agency: Agency,
        result: Optional[Dict[str, Any]] = None,
    ) -> Agency:
        """Agency 모델 통계를 갱신합니다."""
        agency.total_notices = Notice.objects.active().filter(agency=agency).count()
        agency.last_crawl_at = timezone.now()
        if result is not None:
            agency.last_crawl_status = result.get('status', '')
        agency.save()
        return agency
