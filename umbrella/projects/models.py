from django.db import models
from confluence.models import Space
from google.models import DriveFolder

# Create your models here.
class Project(models.Model):
    name = models.CharField(max_length=32, default='TRD05', unique=True)
    description = models.TextField(max_length=255, blank=True)
    confluence_space = models.ForeignKey(Space, on_delete=models.PROTECT, blank=True, null=True)
    google_drive_folder = models.ForeignKey(DriveFolder, on_delete=models.PROTECT, blank=True, null=True)

    def __str__(self):
        return self.name

