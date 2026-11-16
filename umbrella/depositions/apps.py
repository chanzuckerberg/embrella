from django.apps import AppConfig


class DepositionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "depositions"

    def ready(self):
        from . import signals  # noqa: F401
