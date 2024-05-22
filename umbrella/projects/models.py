from django.db import models
from confluence.models import Space
from google.models import DriveFolder
from umbrella.choices import PROJECT_NAMES

# Create your models here.
class Project(models.Model):
    name = models.CharField(max_length=32, default='TRD05', unique=True)
    description = models.TextField(max_length=255, blank=True)
    confluence_space = models.ForeignKey(Space, on_delete=models.PROTECT)
    google_drive_folder = models.ForeignKey(DriveFolder, on_delete=models.PROTECT)

    def __str__(self):
        return self.name

