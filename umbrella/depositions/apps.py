from django.apps import AppConfig


class DepositionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "depositions"

    def ready(self):
        from django.db.models.signals import post_migrate

        post_migrate.connect(_ensure_syncer_reconciler_schedule, sender=self)


def _ensure_syncer_reconciler_schedule(sender, using=None, **kwargs):
    """Register the periodic task that restarts orphaned deposition job syncers (once; admin edits kept)."""
    from django_q.models import Schedule

    Schedule.objects.using(using).get_or_create(
        name="deposition_syncer_reconciler",
        defaults={
            "func": "depositions.tasks.reconcile_deposition_syncers",
            "schedule_type": Schedule.MINUTES,
            "minutes": 5,
            "repeats": -1,
        },
    )
