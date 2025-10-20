# signals.py

from django.contrib.auth import get_user
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import MsiSession


@receiver(pre_save, sender=MsiSession)
def set_user(sender, instance, **kwargs):
    if not instance.pk:  # Only set user on creation
        instance.user = get_user(instance.request)
