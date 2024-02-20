from django.db import models
from umbrella.choices import GOOGLE_DRIVE_FOLDERS

class DriveFolder(models.Model):
    name = models.CharField(max_length=6, default='BD01', unique=True, choices=GOOGLE_DRIVE_FOLDERS)
    url = models.URLField()

    def __str__(self):
        return self.get_name_display()



