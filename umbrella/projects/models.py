from django.contrib.auth.models import User
from django.db import models
from external_links.models import ExternalResource


# Create your models here.
class Project(models.Model):
    name = models.CharField(max_length=32, default="TRD05", unique=True)
    description = models.TextField(max_length=255, blank=True)
    project_leader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    # Unified documentation field
    documentation_space = models.ForeignKey(
        ExternalResource,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="project_doc_spaces",
        limit_choices_to={"resource_type": "doc_space"},
        help_text="Project documentation workspace (Confluence, Google Drive, Benchling, etc.)",
    )

    def __str__(self):
        return self.name
