from django.apps import AppConfig
from django.conf import settings

import db_pool


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        # Import tasks to start the background worker when the app is loaded
        db_pool.init_db(settings)
        from . import tasks  # noqa: F401

