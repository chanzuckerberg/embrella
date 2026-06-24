from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

# ORCID iDs are 16 digits grouped in fours; the final character is a checksum
# that may be the digit's value or the letter ``X``. Stored as ``xxxx-xxxx-xxxx-xxxx``.
orcid_validator = RegexValidator(
    regex=r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$",
    message="ORCID iD must be formatted as xxxx-xxxx-xxxx-xxxx.",
)


class Institution(models.Model):
    name = models.CharField(max_length=255)
    ror_id = models.CharField(
        max_length=32,
        blank=True,
        help_text="Research Organization Registry id (optional).",
    )
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=128, blank=True)
    country = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Person(models.Model):
    """Canonical directory entry for a person, deduplicated by ORCID."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="person",
        help_text="Optional link to a logged-in account.",
    )
    orcid = models.CharField(
        max_length=19,
        unique=True,
        null=True,
        blank=True,
        validators=[orcid_validator],
        help_text="ORCID iD as xxxx-xxxx-xxxx-xxxx. Null so records without an ORCID don't collide.",
    )
    given_name = models.CharField(max_length=128)
    family_name = models.CharField(max_length=128)
    contact_email = models.EmailField(
        blank=True,
        help_text="Preferred contact email; may differ from the email used to sign in to the app.",
    )
    institution = models.ForeignKey(
        Institution,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="people",
        help_text="The single institution this person is affiliated with.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["family_name", "given_name"]

    def __str__(self):
        return f"{self.given_name} {self.family_name}".strip()
