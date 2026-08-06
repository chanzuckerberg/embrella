from django.contrib.auth.models import User
from django.db import models
from tem.models import MsiSession


class Deposition(models.Model):
    # No status field — status is per-dataset (see Dataset.status). A deposition-level status, if ever needed, is a derived rollup of its datasets.
    deposition_id = models.IntegerField(null=True, unique=True, blank=True, help_text="Assigned by reservation service")
    title = models.CharField(max_length=256)
    description = models.TextField(blank=True)
    submitter_user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="depositions"
    )
    deposition_publications = models.TextField(blank=True)
    related_database_entries = models.TextField(blank=True)
    authors_json = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordered list of {author_id, is_primary, is_corresponding, author_list_order}; "
        "author_id soft-references users.Author (not a FK).",
    )
    release_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Deposition {self.deposition_id or self.pk} — {self.title}"


class Dataset(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("syncing", "Syncing"),
        ("pushed", "Pushed"),
        ("failed", "Failed"),
    ]

    deposition = models.ForeignKey(Deposition, on_delete=models.CASCADE, related_name="datasets")
    dataset_id = models.IntegerField(null=True, unique=True, blank=True, help_text="Assigned by reservation service")
    title = models.CharField(max_length=256)
    description = models.TextField(blank=True)
    sample_preparation = models.TextField(blank=True)
    grid_preparation = models.TextField(blank=True)
    other_setup = models.TextField(blank=True, help_text="Free-text experimental notes (portal: dataset.other_setup)")
    assay_label = models.CharField(max_length=256, blank=True)
    assay_ontology_id = models.CharField(max_length=256, blank=True)
    is_authors_same_as_deposition = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
        db_index=True,
        help_text="Display/submission status; written by the syncer from DatasetJob.state.",
    )
    sample = models.ForeignKey(
        "cryo_grids.Sample",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="datasets",
        help_text="The biological sample this dataset describes. Sample identity fields "
        "(organism, tissue, cell_type, cell_strain, cell_component, sample_type) "
        "live on cryo_grids.Sample.",
    )
    authors_json = models.JSONField(
        default=list,
        blank=True,
        help_text="Only used when is_authors_same_as_deposition=False. Same shape as Deposition.authors_json.",
    )
    dataset_publications = models.TextField(blank=True)
    related_database_entries = models.TextField(blank=True)
    TOMOGRAM_SUBSET_CHOICES = [
        ("all", "All from AreTomo runs"),
        ("annotated", "Only tomograms with annotations"),
        ("custom", "Custom CSV (per-row override)"),
    ]
    tomogram_subset_mode = models.CharField(
        max_length=16,
        choices=TOMOGRAM_SUBSET_CHOICES,
        default="all",
        help_text="How the tomogram subset is chosen; applies to ALL sessions in this dataset.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Dataset {self.dataset_id or self.pk} — {self.title}"


class DatasetFunding(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="funding")
    funding_agency_name = models.CharField(max_length=256)
    grant_id = models.CharField(max_length=256, blank=True)

    def __str__(self):
        return f"{self.funding_agency_name} ({self.grant_id})"


class DatasetJob(models.Model):
    STATE_CHOICES = [
        ("pending", "Pending"),
        ("prep_submitted", "Prep Submitted"),
        ("prep_running", "Prep Running"),
        ("prep_completed", "Prep Completed"),
        ("push_submitted", "Push Submitted"),
        ("push_running", "Push Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    dataset = models.OneToOneField(Dataset, on_delete=models.CASCADE, related_name="job")
    prep_slurm_job_id = models.CharField(max_length=32, null=True, blank=True)
    push_slurm_job_id = models.CharField(max_length=32, null=True, blank=True)
    state = models.CharField(max_length=256, choices=STATE_CHOICES, default="pending", db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    log_excerpt = models.TextField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"DatasetJob {self.pk} ({self.state}) for Dataset {self.dataset_id}"


class DepositionSession(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="sessions")
    msi_session = models.ForeignKey(MsiSession, on_delete=models.CASCADE, related_name="deposition_sessions")
    aretomo_run_name = models.CharField(max_length=40, blank=True)
    denoise_run_name = models.CharField(max_length=40, blank=True, help_text="Blank means denoise was skipped")
    subset_csv_path = models.CharField(max_length=1024, blank=True)
    selected_copick_runs = models.JSONField(default=list, blank=True)
    last_autofill_at = models.DateTimeField(null=True, blank=True)
    last_autofill_duration_seconds = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        unique_together = ["dataset", "msi_session"]

    def __str__(self):
        return f"DepositionSession {self.pk} — {self.msi_session}"


class TiltseriesMetadata(models.Model):
    QUALITY_CHOICES = [(i, str(i)) for i in range(1, 6)]

    session = models.OneToOneField(DepositionSession, on_delete=models.CASCADE, related_name="tiltseries_metadata")
    acceleration_voltage = models.FloatField(null=True, blank=True)
    spherical_aberration_constant = models.FloatField(null=True, blank=True)
    microscope_manufacturer = models.CharField(max_length=256, blank=True)
    microscope_model = models.CharField(max_length=256, blank=True)
    microscope_energy_filter = models.CharField(max_length=256, blank=True)
    microscope_image_corrector = models.CharField(max_length=256, blank=True)
    microscope_phase_plate = models.CharField(max_length=256, blank=True)
    camera_manufacturer = models.CharField(max_length=256, blank=True)
    camera_model = models.CharField(max_length=256, blank=True)
    tilt_min = models.FloatField(null=True, blank=True)
    tilt_max = models.FloatField(null=True, blank=True)
    tilt_step = models.FloatField(null=True, blank=True)
    tilting_scheme = models.CharField(max_length=256, blank=True)
    tilt_axis = models.FloatField(null=True, blank=True)
    total_flux = models.FloatField(null=True, blank=True)
    data_acquisition_software = models.CharField(max_length=256, blank=True)
    pixel_spacing = models.FloatField(null=True, blank=True)
    is_aligned = models.BooleanField(null=True, blank=True)
    aligned_tiltseries_binning = models.IntegerField(null=True, blank=True)
    binning_from_frames = models.FloatField(null=True, blank=True)
    tilt_series_quality = models.IntegerField(null=True, blank=True, choices=QUALITY_CHOICES)
    autofill_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"TiltseriesMetadata for session {self.session_id}"


class TomogramMetadata(models.Model):
    session = models.OneToOneField(DepositionSession, on_delete=models.CASCADE, related_name="tomogram_metadata")
    voxel_spacing = models.FloatField(null=True, blank=True)
    ctf_corrected = models.BooleanField(null=True, blank=True)
    fiducial_alignment_status = models.CharField(max_length=256, blank=True)
    reconstruction_method = models.CharField(max_length=256, blank=True)
    reconstruction_software = models.CharField(max_length=256, blank=True)
    processing = models.CharField(max_length=256, blank=True)
    processing_software = models.CharField(max_length=256, blank=True)
    is_visualization_default = models.BooleanField(default=False)
    autofill_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"TomogramMetadata for session {self.session_id}"


class DepositionAnnotation(models.Model):
    COPICK_KIND_CHOICES = [
        ("picks", "Picks"),
        ("segmentations", "Segmentations"),
        ("meshes", "Meshes"),
    ]
    METHOD_TYPE_CHOICES = [
        ("manual", "Manual"),
        ("automated", "Automated"),
        ("hybrid", "Hybrid"),
        ("simulated", "Simulated"),
    ]
    session = models.ForeignKey(DepositionSession, on_delete=models.CASCADE, related_name="annotations")
    copick_kind = models.CharField(max_length=256, choices=COPICK_KIND_CHOICES)
    copick_ref = models.CharField(max_length=256)
    object_id = models.CharField(max_length=256, blank=True)
    object_name = models.CharField(max_length=256, blank=True)
    object_description = models.TextField(blank=True)
    object_state = models.CharField(max_length=256, blank=True)
    object_count = models.IntegerField(null=True, blank=True)
    annotation_method = models.CharField(max_length=256, blank=True)
    annotation_software = models.CharField(max_length=256, blank=True)
    annotation_publication = models.TextField(blank=True)
    method_type = models.CharField(max_length=256, blank=True, choices=METHOD_TYPE_CHOICES)
    ground_truth_status = models.BooleanField(default=False)
    is_visualization_default = models.BooleanField(
        default=False, help_text="should this annotation be the DEFAULT shown in the portal viewer?"
    )
    is_selected = models.BooleanField(default=True, help_text="should this annotation be INCLUDED in the deposition")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        unique_together = ["session", "copick_kind", "copick_ref"]

    def __str__(self):
        return f"Annotation {self.object_name} ({self.copick_kind}) — session {self.session_id}"


class DepositionAnnotationMethodLink(models.Model):
    LINK_TYPE_CHOICES = [
        ("documentation", "Documentation"),
        ("models_weights", "Models/Weights"),
        ("other", "Other"),
        ("source_code", "Source Code"),
        ("website", "Website"),
    ]
    annotation = models.ForeignKey(DepositionAnnotation, on_delete=models.CASCADE, related_name="method_links")
    link_type = models.CharField(max_length=256, choices=LINK_TYPE_CHOICES)
    link = models.URLField(max_length=1024)
    custom_name = models.CharField(max_length=256, blank=True)

    def __str__(self):
        return f"{self.link_type}: {self.link}"
