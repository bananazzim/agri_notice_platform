from __future__ import annotations

from django.core.management.base import BaseCommand

from scheduler.scheduler import create_scheduler


class Command(BaseCommand):
    help = "Start APScheduler for daily notice crawling."

    def add_arguments(self, parser):
        parser.add_argument(
            "--run-once",
            action="store_true",
            help="Run the crawler job immediately after scheduler startup.",
        )
        parser.add_argument(
            "--no-block",
            action="store_true",
            help="Start scheduler and return immediately. Mostly useful for tests.",
        )

    def handle(self, *args, **options):
        scheduler = create_scheduler()
        scheduler.start(run_once=options["run_once"])

        self.stdout.write(self.style.SUCCESS("Scheduler started. Daily job: 09:00 Asia/Seoul"))

        if options["no_block"]:
            scheduler.stop()
            return

        scheduler.serve_forever()
