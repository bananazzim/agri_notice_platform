from django.apps import AppConfig


class NoticesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notices'
    verbose_name = '공고 관리'

    def ready(self):
        """앱 시작 시 신호 등록"""
        import apps.notices.signals  # noqa
