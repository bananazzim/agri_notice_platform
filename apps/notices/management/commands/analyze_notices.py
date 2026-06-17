from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Disabled. OpenAI analysis runs only when a user opens a notice detail page."

    def add_arguments(self, parser):
        parser.add_argument("--id", dest="notice_id", help="Analyze a single notice UUID.")
        parser.add_argument("--limit", type=int, default=50, help="Maximum notices to analyze.")
        parser.add_argument(
            "--reanalyze",
            action="store_true",
            help="Analyze notices even if AI analysis already exists.",
        )

    def handle(self, *args, **options):
        raise CommandError(
            "Batch AI analysis is disabled to control API cost. "
            "Open a notice detail page to analyze that single notice, "
            "or use check_openai only for a one-notice connectivity test."
        )
