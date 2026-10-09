from django.conf import settings
from django.contrib.auth.models import Group, User
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

    # Access: users with a role. Kept in sync with the role groups below.
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="ProjectMembership",
        related_name="projects",
        blank=True,
    )

    # Grantees for object permissions (guardian grants only to users or groups).
    # One group per role; each member sits in exactly one.
    viewer_group = models.OneToOneField(
        Group,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    editor_group = models.OneToOneField(
        Group,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    # Descriptive only: credit and deposition metadata, no access.
    institutions = models.ManyToManyField("people.Institution", blank=True, related_name="projects")
    contributors = models.ManyToManyField("people.Person", blank=True, related_name="projects")

    def __str__(self):
        return self.name


class ProjectRole(models.TextChoices):
    VIEWER = "viewer", "Viewer"
    EDITOR = "editor", "Editor"


class ProjectMembership(models.Model):
    """A user's role in a project."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_memberships",
    )
    role = models.CharField(max_length=16, choices=ProjectRole.choices, default=ProjectRole.VIEWER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "user"], name="unique_project_member"),
        ]

    def __str__(self):
        return f"{self.user} @ {self.project} ({self.role})"
