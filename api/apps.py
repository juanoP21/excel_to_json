from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        # Import tasks to start the background worker when the app is loaded
        from . import tasks  # noqa: F401

