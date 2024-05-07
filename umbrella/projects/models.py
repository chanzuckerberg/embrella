from django.db import models
from confluence.models import Space
from google.models import DriveFolder
from umbrella.choices import PROJECT_NAMES

# Create your models here.
class Project(models.Model):
    name = models.CharField(max_length=6, choices=PROJECT_NAMES,  default='TRD05', unique=True)
    confluence_space = models.ForeignKey(Space, on_delete=models.PROTECT)
    google_drive_folder = models.ForeignKey(DriveFolder, on_delete=models.PROTECT)

    def __str__(self):
        return self.get_name_display()

