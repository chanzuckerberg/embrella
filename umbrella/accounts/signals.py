from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .cluster_usernames import clear_username_cache
from .models import Profile, UserClusterCredentials


@receiver([post_save, post_delete], sender=UserClusterCredentials)
def _invalidate_username_cache(sender, **kwargs):
    clear_username_cache()


@receiver(post_save, sender=get_user_model())
def _ensure_profile(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        Profile.objects.get_or_create(user=instance)
