from django.apps import AppConfig
from django.core.cache import cache

class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        # Clear session data when the server starts
        cache.clear()