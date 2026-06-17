from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.utils import timezone

from ai.analyzer import NoticeAnalysisResult, OpenAINoticeAnalyzer
from apps.notices.models import Notice
from core.exceptions import AIAnalysisError
from core.logger import ai_logger
from services.scoring_service import should_request_ai


@dataclass(frozen=True)
class NoticeAIOutcome:
    notice_id: str
    analyzed: bool
    skipped: bool
    reason: str
    provider: str = ""


class NoticeAIService:
    """Control when OpenAI is called and how AI results are persisted."""

    def __init__(self, analyzer: OpenAINoticeAnalyzer | None = None) -> None:
        self.analyzer = analyzer or OpenAINoticeAnalyzer(use_fallback=False)

    def analyze_notice(
        self,
        notice: Notice,
        *,
        user_opened_detail: bool = False,
        admin_requested: bool = False,
        force: bool = False,
    ) -> NoticeAIOutcome:
        already_analyzed = self._already_analyzed(notice)
        if already_analyzed and not force:
            return NoticeAIOutcome(str(notice.pk), analyzed=False, skipped=True, reason="already_analyzed")
        if notice.ai_analysis_status == "failed" and not admin_requested and not force:
            return NoticeAIOutcome(str(notice.pk), analyzed=False, skipped=True, reason="previous_failure")

        if not self.can_analyze(
            notice,
            user_opened_detail=user_opened_detail,
            admin_requested=admin_requested,
            already_analyzed=False if force else already_analyzed,
        ):
            self._mark_skipped(notice)
            return NoticeAIOutcome(str(notice.pk), analyzed=False, skipped=True, reason="not_eligible")

        try:
            result = self.analyzer.analyze_notice_data(self._build_payload(notice))
            if result.provider != "openai":
                raise AIAnalysisError("AI analyzer returned a non-OpenAI fallback result.")
        except Exception as exc:
            self._mark_failed(notice, exc)
            return NoticeAIOutcome(str(notice.pk), analyzed=False, skipped=False, reason="failed")

        self._save_success(notice, result)
        return NoticeAIOutcome(
            str(notice.pk),
            analyzed=True,
            skipped=False,
            reason="success",
            provider=result.provider,
        )

    def can_analyze(
        self,
        notice: Notice,
        *,
        user_opened_detail: bool = False,
        admin_requested: bool = False,
        already_analyzed: bool | None = None,
    ) -> bool:
        return should_request_ai(
            {
                "title": notice.title,
                "category": notice.category,
                "deadline": notice.deadline,
                "ai_tags": notice.ai_tags,
                "recommended_for": notice.recommended_for,
            },
            notice.agency,
            user_opened_detail=user_opened_detail,
            admin_requested=admin_requested,
            already_analyzed=self._already_analyzed(notice) if already_analyzed is None else already_analyzed,
        )

    def analyze_queryset(
        self,
        queryset: Any,
        *,
        limit: int = 50,
        admin_requested: bool = False,
        force: bool = False,
    ) -> list[NoticeAIOutcome]:
        outcomes: list[NoticeAIOutcome] = []
        for notice in queryset.select_related("agency")[:limit]:
            outcomes.append(
                self.analyze_notice(
                    notice,
                    admin_requested=admin_requested,
                    force=force,
                )
            )
        return outcomes

    def _build_payload(self, notice: Notice) -> dict[str, str]:
        return {
            "agency": notice.agency.name,
            "title": notice.title,
            "category": notice.category,
            "content": (notice.content or notice.summary or "")[:1000],
        }

    def _save_success(self, notice: Notice, result: NoticeAnalysisResult) -> None:
        notice.ai_summary = result.summary
        notice.ai_tags = result.tags
        notice.importance_score = result.importance_score
        notice.recommended_for = result.recommended_for
        notice.score_source = "ai"
        notice.ai_analysis_status = "success"
        notice.ai_analysis_error = ""
        notice.ai_analyzed_at = timezone.now()
        notice.save(update_fields=[
            "ai_summary",
            "ai_tags",
            "importance_score",
            "recommended_for",
            "score_source",
            "ai_analysis_status",
            "ai_analysis_error",
            "ai_analyzed_at",
            "updated_at",
        ])

    def _mark_skipped(self, notice: Notice) -> None:
        if notice.ai_analysis_status == "skipped":
            return
        notice.ai_analysis_status = "skipped"
        notice.save(update_fields=["ai_analysis_status", "updated_at"])

    def _mark_failed(self, notice: Notice, exc: Exception) -> None:
        error_message = str(exc)[:1000]
        notice.importance_score = notice.rule_score
        notice.score_source = "rule"
        notice.ai_analysis_status = "failed"
        notice.ai_analysis_error = error_message
        notice.save(update_fields=[
            "importance_score",
            "score_source",
            "ai_analysis_status",
            "ai_analysis_error",
            "updated_at",
        ])
        ai_logger.warning("AI analysis failed for notice %s: %s", notice.pk, error_message)

    def _already_analyzed(self, notice: Notice) -> bool:
        return bool(notice.ai_analyzed_at and notice.ai_summary and notice.ai_analysis_status == "success")
