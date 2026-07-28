from django.apps import AppConfig


class BackendConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend'

    def ready(self):
        from background_jobs.scheduler import start_scheduler
        start_scheduler()
