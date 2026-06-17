from __future__ import annotations

import signal
import time
from dataclasses import dataclass
from typing import Any

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, JobExecutionEvent
from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone

from core.logger import scheduler_logger


@dataclass(frozen=True)
class SchedulerJobConfig:
    job_id: str = "daily_notice_crawl"
    hour: int = 9
    minute: int = 0
    timezone: str = "Asia/Seoul"
    max_instances: int = 1
    coalesce: bool = True


class AgriNoticeScheduler:
    """APScheduler wrapper for recurring crawler jobs."""

    def __init__(self, job_config: SchedulerJobConfig | None = None) -> None:
        self.job_config = job_config or SchedulerJobConfig()
        self.scheduler = BackgroundScheduler(
            timezone=self.job_config.timezone,
            job_defaults={
                "coalesce": self.job_config.coalesce,
                "max_instances": self.job_config.max_instances,
                "misfire_grace_time": 60 * 30,
            },
        )
        self._shutdown_requested = False

    def start(self, run_once: bool = False) -> None:
        self._register_listeners()
        self._register_jobs()
        self.scheduler.start()
        scheduler_logger.info("Scheduler started")

        if run_once:
            self.run_daily_crawl()

    def stop(self) -> None:
        self._shutdown_requested = True
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            scheduler_logger.info("Scheduler stopped")

    def serve_forever(self, poll_interval: float = 1.0) -> None:
        self._install_signal_handlers()
        try:
            while not self._shutdown_requested:
                time.sleep(poll_interval)
        finally:
            self.stop()

    def run_daily_crawl(self) -> None:
        started_at = timezone.now()
        scheduler_logger.info("Daily crawler job started at %s", started_at.isoformat())

        try:
            call_command("run_crawler")
        except Exception as exc:
            scheduler_logger.error("Daily crawler job failed: %s", exc, exc_info=True)
            raise

        finished_at = timezone.now()
        duration = (finished_at - started_at).total_seconds()
        scheduler_logger.info("Daily crawler job finished in %.2fs", duration)

    def _register_jobs(self) -> None:
        config = self.job_config
        self.scheduler.add_job(
            self.run_daily_crawl,
            trigger="cron",
            id=config.job_id,
            hour=config.hour,
            minute=config.minute,
            replace_existing=True,
        )
        scheduler_logger.info(
            "Registered job %s at %02d:%02d %s",
            config.job_id,
            config.hour,
            config.minute,
            config.timezone,
        )

    def _register_listeners(self) -> None:
        self.scheduler.add_listener(
            self._log_job_event,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR,
        )

    def _log_job_event(self, event: JobExecutionEvent) -> None:
        if event.exception:
            scheduler_logger.error(
                "Scheduled job failed: %s\n%s",
                event.job_id,
                event.traceback or event.exception,
            )
            return

        scheduler_logger.info("Scheduled job succeeded: %s", event.job_id)

    def _install_signal_handlers(self) -> None:
        def handle_signal(signum: int, frame: Any) -> None:
            scheduler_logger.info("Shutdown signal received: %s", signum)
            self.stop()

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)


def get_scheduler_config() -> SchedulerJobConfig:
    raw_config = getattr(settings, "NOTICE_SCHEDULER", {})
    return SchedulerJobConfig(
        hour=int(raw_config.get("hour", 9)),
        minute=int(raw_config.get("minute", 0)),
        timezone=str(raw_config.get("timezone", "Asia/Seoul")),
    )


def create_scheduler() -> AgriNoticeScheduler:
    return AgriNoticeScheduler(get_scheduler_config())
