from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.notices.models import Notice
from services.ai_service import NoticeAIService


class Command(BaseCommand):
    help = "Check OpenAI configuration and optionally run one real notice analysis."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only check settings and installed SDK. Does not call OpenAI.",
        )
        parser.add_argument(
            "--id",
            dest="notice_id",
            help="Analyze a specific notice UUID. If omitted, one high-value active notice is used.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Reanalyze even if the notice already has an AI result.",
        )

    def handle(self, *args, **options):
        config = getattr(settings, "AI_CONFIG", {})
        api_key = str(config.get("api_key") or "")
        model = str(config.get("model") or "")
        max_tokens = config.get("max_tokens")

        self.stdout.write(f"OpenAI model: {model or '(not configured)'}")
        self.stdout.write(f"OpenAI max tokens: {max_tokens}")
        self.stdout.write(f"OpenAI API key configured: {'yes' if api_key else 'no'}")

        try:
            import openai
        except ImportError as exc:
            raise CommandError("openai package is not installed.") from exc

        self.stdout.write(f"openai package: {getattr(openai, '__version__', 'unknown')}")

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Dry run complete. No API request was sent."))
            return

        if not api_key:
            raise CommandError("OPENAI_API_KEY is not configured in .env.")

        notice = self._get_notice(options.get("notice_id"))
        self.stdout.write(f"Testing notice: {notice.title} ({notice.pk})")

        outcome = NoticeAIService().analyze_notice(
            notice,
            user_opened_detail=True,
            force=options["force"],
        )
        notice.refresh_from_db()

        if outcome.analyzed:
            self.stdout.write(self.style.SUCCESS("OpenAI analysis succeeded."))
            self.stdout.write(f"AI tags: {', '.join(notice.ai_tags)}")
            self.stdout.write(f"AI score: {notice.importance_score}")
            return

        if outcome.skipped:
            self.stdout.write(
                self.style.WARNING(
                    f"OpenAI analysis skipped: {outcome.reason}. Use --force to reanalyze cached notices."
                )
            )
            return

        error = (notice.ai_analysis_error or "unknown error").strip()
        raise CommandError(f"OpenAI analysis failed: {error}")

    def _get_notice(self, notice_id: str | None) -> Notice:
        queryset = Notice.objects.active().select_related("agency")

        if notice_id:
            try:
                return queryset.get(pk=notice_id)
            except Notice.DoesNotExist as exc:
                raise CommandError(f"Notice not found: {notice_id}") from exc

        notice = (
            queryset.filter(importance_score__gte=70)
            .exclude(content="")
            .order_by("-importance_score", "-posted_date", "-created_at")
            .first()
        )
        if notice is None:
            raise CommandError("No active high-value notice with content was found.")

        return notice
