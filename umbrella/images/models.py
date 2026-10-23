import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from projects.models import Project
from simple_history.models import HistoricalRecords


def _upload_path(instance, filename):
    """Bucket files by month; names are chosen by images.services, e.g. images/2026/10/<uuid>_thumb.webp."""
    return f"images/{timezone.now():%Y/%m}/{filename}"


class Image(models.Model):
    """An uploaded image plus its display copies. Owners link to it, e.g. cryo_grids.GridImage."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Mirrors the owner's project; kept for future project-based permissions
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="images")

    original = models.FileField(upload_to=_upload_path, max_length=255)
    preview = models.FileField(upload_to=_upload_path, max_length=255)
    thumb = models.FileField(upload_to=_upload_path, max_length=255)

    original_name = models.CharField(max_length=255, help_text="Filename as uploaded; used for downloads")
    content_type = models.CharField(max_length=50, help_text="Detected from the file's bytes, e.g. image/tiff")
    size_bytes = models.PositiveBigIntegerField()
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()

    notes = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_images",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Keeps a deleted image's name for the grid timeline; notes edits aren't worth tracking
    history = HistoricalRecords(excluded_fields=["notes"])

    def __str__(self):
        return self.original_name
