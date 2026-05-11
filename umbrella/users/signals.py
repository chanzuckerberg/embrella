from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import UserClusterCredentials
from .usernames import clear_username_cache


@receiver([post_save, post_delete], sender=UserClusterCredentials)
def _invalidate_username_cache(sender, **kwargs):
    clear_username_cache()
