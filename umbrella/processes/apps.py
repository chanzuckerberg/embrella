from django.apps import AppConfig


class ProcessesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "processes"

    def ready(self):
        from processes.services.cluster_resolver import connect_cache_invalidation

        connect_cache_invalidation()
