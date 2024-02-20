from django.db import models
from umbrella.choices import CONFLUENCE_SPACE_NAMES

class Space(models.Model):
    name = models.CharField(max_length=6, choices=CONFLUENCE_SPACE_NAMES,  default='BD01', unique=True)
    space_id = models.CharField(max_length=50, unique=True)
    url = models.URLField()

    def __str__(self):
        return self.url



