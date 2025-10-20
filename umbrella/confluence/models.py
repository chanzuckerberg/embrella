from django.db import models


class Space(models.Model):
    name = models.CharField(max_length=32,  default='BD01', unique=True)
    space_id = models.CharField(max_length=50, unique=True)
    url = models.URLField()

    def __str__(self):
        return self.url

class Page(models.Model):
    name = models.CharField(max_length=32,  default='sample prep notes')
    url = models.URLField()

    class Meta:
        unique_together = [["name","url"]]

    def __str__(self):
        return self.name



