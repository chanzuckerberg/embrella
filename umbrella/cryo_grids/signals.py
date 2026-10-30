"""Keep grid images in step with their grid, whichever code path saves or deletes it."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from images import services as image_services
from images.models import Image

from cryo_grids import services
from cryo_grids.models import CryoGrid, GridImage

# update_fields names that can carry a project change
PROJECT_FIELDS = {services.PROJECT_FIELD, f"{services.PROJECT_FIELD}_id"}


@receiver(post_save, sender=CryoGrid)
def _sync_image_project(sender, instance, created, raw=False, update_fields=None, **kwargs):
    # New grids have no images; partial saves that skip the project can't move them
    if raw or created:
        return

    if update_fields is not None and not PROJECT_FIELDS & set(update_fields):
        return

    services.sync_image_project(instance)


@receiver(post_delete, sender=GridImage)
def _delete_image(sender, instance, origin=None, **kwargs):
    """A hard-deleted grid takes its images (rows and files) with it. Trashing keeps them."""
    # Deleting the image itself cascaded here; it's already handled
    if isinstance(origin, Image) or getattr(origin, "model", None) is Image:
        return

    image = Image.objects.filter(pk=instance.image_id).first()
    if image:
        image_services.delete(image)
