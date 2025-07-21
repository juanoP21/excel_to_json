from django.apps import AppConfig
from django.conf import settings

import db_pool


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        # Import tasks to start the background worker when the app is loaded
        db_pool.init_db(settings)
        # Initialize the pool and sync Django DB settings with the active host
        try:
            db_pool.initialize_pool()
            db_pool.apply_django_db_settings(settings)
        except Exception as exc:
            # Log but allow startup so failover logic can retry later
            print(f"DB pool initialization error: {exc}")
        from . import tasks  # noqa: F401

