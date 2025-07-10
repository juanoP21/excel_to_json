from django.apps import AppConfig


class PdfconvertConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pdfconvert'

    def ready(self):
        # Import tasks to ensure the background worker starts when the app is
        # loaded. The import has side effects (spawns the worker thread).
        from . import tasks  # noqa: F401
