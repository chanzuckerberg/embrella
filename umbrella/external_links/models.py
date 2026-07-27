"""
Models for external documentation links.

Tracks links to external systems where scientists maintain project documentation,
lab notebooks, protocols, and related information.
"""

from django.db import models


class ExternalResource(models.Model):
    """
    Generic external documentation/information resource.

    Tracks links to external systems where scientists maintain project documentation,
    lab notebooks, protocols, and related information. Supports any documentation
    system without requiring code changes.

    Examples:
        - Confluence wiki space for a project
        - Google Drive folder for project files
        - Benchling project for protocols
        - Specific Confluence page for sample prep notes

    Note:
        This is for DOCUMENTATION links, not data storage. Raw microscopy data
        is stored on HPC cluster storage (/hpc/instruments/).
    """

    RESOURCE_TYPE_CHOICES = [
        ("doc_space", "Documentation Space"),
        ("doc_page", "Documentation Page"),
    ]

    resource_type = models.CharField(
        max_length=20, choices=RESOURCE_TYPE_CHOICES, help_text="Type of documentation resource"
    )
    system_name = models.CharField(
        max_length=50, help_text="Documentation system name (e.g., 'Confluence', 'Google Drive', 'Benchling', 'Notion')"
    )
    name = models.CharField(max_length=100, help_text="Display name for this resource")
    url = models.URLField(unique=True, help_text="Full URL to the documentation resource")
    metadata = models.JSONField(
        default=dict, blank=True, help_text="System-specific fields (e.g., {'space_id': 'CHOL'} for Confluence)"
    )

    class Meta:
        indexes = [
            models.Index(fields=["resource_type", "system_name"]),
        ]
        verbose_name = "External Resource"
        verbose_name_plural = "External Resources"

    def __str__(self):
        return f"{self.system_name} - {self.name}"
