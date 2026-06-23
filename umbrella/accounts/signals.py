from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .cluster_usernames import clear_username_cache
from .models import UserClusterCredentials


@receiver([post_save, post_delete], sender=UserClusterCredentials)
def _invalidate_username_cache(sender, **kwargs):
    clear_username_cache()
