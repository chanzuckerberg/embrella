import sys
import uuid

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.timezone import now
from stores.models import Cluster, DataKind, FilePattern, Path, PathType
from tem.models import Microscope, MsiSession, SessionPlan, Software
from umbrella_logger import logger

"""
from stores.models import DataRecord,
class ArrayData(DataRecord):
    unit_cell_dimension
    is_stack
    sub_array_of
"""


def getattr_from_globals(attr_name):
    # get attributes of this python module
    all_attrs = globals()
    my_attr = None
    for name, value in all_attrs.items():
        if name == attr_name:
            my_attr = value
            break
    if not my_attr:
        raise ValueError("%s not an attribute of module %s" % (attr_name, __file__))
    return my_attr


"""
PathData
    name
    variables
    pattern
"""


class Task(models.Model):
    name = models.CharField(max_length=255, default="motion correction")
    step = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return "%d-%s" % (self.step, self.name)


class ProcSoftware(models.Model):
    """
    A software program started with the same command with different options.

    Fields:
    - processor_class: Python class name for execution (e.g., 'aretomo3')
    - default_cluster: Default cluster for job submission ('czii' or 'bruno')
    - allowed_clusters: List of clusters this software can run on
    - processing_root: Optional PathType to directory template
    - script_dir: Optional PathType to script location
    """

    name = models.CharField(
        max_length=32,
        default="aretomo3",
        help_text=("Filesystem token, not a display name: fills {proc_software} in stores.Path."),
    )
    version = models.CharField(max_length=32, default="2024-03-10")
    capable_tasks = models.ManyToManyField(Task)

    # Legacy field - deprecated in favor of processor_class
    callback_function = models.CharField(
        max_length=32, default="run_aretomo3", help_text="Deprecated: use processor_class"
    )

    # New generic execution fields
    processor_class = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        unique=True,
        help_text='Processor class name (e.g., "aretomo3" maps to AreTomo3Processor)',
    )
    default_cluster = models.CharField(
        max_length=16,
        choices=[("czii", "CZII"), ("bruno", "Bruno")],
        default="czii",
        help_text="Default cluster for job submission",
    )
    allowed_clusters = models.JSONField(
        default=list,
        blank=True,
        help_text='List of cluster IDs this software can run on (e.g., ["czii", "bruno"]). Empty means all clusters allowed.',
    )
    storage_dirname = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        help_text=(
            "Directory on the cluster this software writes into, used to group the Storage "
            "Explorer. Usually the same as name, but not always: both copick sub-processors "
            "write into 'copick'. Maintained by hand in the admin; blank falls back to name."
        ),
    )
    # PROTECT like every path FK here: SET_NULL is how the None-glob bug arose, and a
    # deleted template must not silently revert a software to the shared layout.
    processing_root = models.ForeignKey(
        PathType,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="processing_root_of",
        help_text=(
            "Directory template for this software's runs, when they live outside the "
            "standard tree. Blank = the shared processing_root template."
        ),
    )
    script_dir = models.ForeignKey(
        PathType,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="script_dir_of",
        help_text=(
            "Directory template for this software's uploaded scripts, when they live "
            "outside the standard tree. Blank = the shared script_dir template."
        ),
    )
    output_patterns = models.ManyToManyField(
        FilePattern,
        blank=True,
        related_name="output_of",
        help_text=(
            "How this software names its output files, at most one pattern per data "
            "kind (e.g. rec volumes, thumbnails, metrics CSV). Read by the syncers and "
            "job templates through BaseProcessor.get_output_pattern()."
        ),
    )
    active = models.BooleanField(
        default=True,
        help_text="Whether this processor is currently active in the codebase",
    )

    logger = models.CharField(max_length=32, default="my_log")

    def __str__(self):
        return "%s @ (%s)" % (self.name, self.version)

    @property
    def dirname(self):
        """Directory segment this software owns on the cluster -- fills {proc_software}.

        Not `name`: the copick sub-processors are distinct softwares writing into one
        `copick` directory, so substituting `name` would resolve to a path that does not
        exist. Currently a no-op for every software that has an output template, since
        those all have `storage_dirname == name`.

        `storage_tree` deliberately spells `dirname or name` at the queryset level instead
        of using this, to avoid instantiating a model per row.
        """
        return self.storage_dirname or self.name


class ParameterDefaults(models.Model):
    """
    Per-processor parameter overrides, cascaded by acquisition software, scope and cluster.

        schema.yaml default
          < row()  < row(software)  < row(scope)  < row(scope+software)
          < row(cluster) < row(cluster+software) < row(cluster+scope) < row(all three)
          < processor.session_defaults()          # e.g. calibrated pixel size

    A blank dimension matches anything. Later rows overwrite earlier ones key by key.
    A JSON null clears the schema default and makes the key required in the launch form.
    """

    # Bit order for `specificity`, least -> most significant. Cluster is the top bit so
    # any cluster row beats any scope/software row: cluster rows mostly hold SLURM
    # resources, which must apply regardless of how the data was acquired.
    DIMENSIONS = ("software", "scope", "cluster")

    proc_software = models.ForeignKey(ProcSoftware, on_delete=models.CASCADE, related_name="parameter_defaults")
    software = models.ForeignKey(
        Software,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Blank = any acquisition software.",
    )
    scope = models.ForeignKey(
        Microscope,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Blank = any microscope.",
    )
    cluster = models.ForeignKey(
        Cluster,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        help_text="Blank = any cluster.",
    )
    values = models.JSONField(
        default=dict,
        blank=True,  # {} is "empty" to the form field; an all-blank row is legal
        help_text="{parameter: value}. Keys must exist in the processor schema. null clears the default.",
    )
    is_active = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name_plural = "parameter defaults"

    def __str__(self):
        dims = ", ".join("%s=%s" % (dim, getattr(self, dim)) for dim in self.DIMENSIONS if getattr(self, dim + "_id"))
        return "%s [%s]" % (self.proc_software.processor_class, dims or "any")

    @property
    def specificity(self) -> int:
        """Bitmask of the dimensions set; higher wins. 0b101 = software + cluster."""
        return sum(1 << bit for bit, dim in enumerate(self.DIMENSIONS) if getattr(self, dim + "_id") is not None)

    @classmethod
    def applicable(
        cls,
        proc_software,
        *,
        software_id: int = None,
        scope_id: int = None,
        cluster_id: str = None,
        exclude_pk: int = None,
    ) -> list:
        """Active rows matching these dimensions, least specific first. Unknown dimension = blank rows only."""
        rows = cls.objects.filter(proc_software=proc_software, is_active=True).exclude(pk=exclude_pk)
        rows = rows.filter(_blank_or("software", software_id))
        rows = rows.filter(_blank_or("scope", scope_id))
        rows = rows.filter(_blank_or("cluster", cluster_id))

        ordered = sorted(rows.select_related(*cls.DIMENSIONS), key=lambda row: (row.specificity, row.pk))
        _warn_on_ties(ordered)
        return ordered

    def clean(self):
        super().clean()
        if not isinstance(self.values, dict):
            raise ValidationError({"values": 'Must be a JSON object, e.g. {"tilt_axis": 85.3}.'})

        # A form error on proc_software leaves it unset; the FK check below still runs.
        if self.proc_software_id is None:
            return

        # The DB can't enforce this: NULLs never collide in a unique index.
        twin = ParameterDefaults.objects.filter(
            proc_software=self.proc_software,
            software=self.software,
            scope=self.scope,
            cluster=self.cluster,
            is_active=True,
        ).exclude(pk=self.pk)
        if twin.exists():
            raise ValidationError("An active row with these exact dimensions already exists (pk %d)." % twin.first().pk)


def _blank_or(field, value):
    """Rows that leave `field` blank, plus rows naming `value` when one is known."""
    blank = Q(**{field + "__isnull": True})
    if value is None:
        return blank
    return blank | Q(**{field: value})


def _warn_on_ties(rows):
    # Ambiguity should be observable, not silently ranked.
    seen = {}
    for row in rows:
        other = seen.setdefault(row.specificity, row)
        if other is not row:
            logger.warning("ParameterDefaults %d and %d have equal specificity; the higher pk wins.", other.pk, row.pk)


class ProcPlan(models.Model):
    """
    A plan for running a single software and producing outputs based on the
    pipes in the plan.
    """

    name = models.CharField(max_length=32, default="czii-live")
    display_name = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Human-readable label for the UI. Falls back to name when blank.",
    )

    def __str__(self):
        return self.name

    @property
    def label(self):
        """
        UI-facing name for the plan.

        `name` feeds path templates via PipeInPlan.get_replacement_map and is
        compared against literals in several views, so it can't be prettified
        in place -- display_name carries the readable label instead.
        """
        return self.display_name or self.name


class Pipe(models.Model):
    """
    A subset of tasks performed by the software that leads to distinguishable outputs
    in the same plan.
    """

    name = models.CharField(max_length=32, default="voxelspacing10.000a")
    software = models.ForeignKey(ProcSoftware, on_delete=models.CASCADE)
    tasks_performed = models.ManyToManyField(Task)
    input = models.ManyToManyField(DataKind, related_name="datakind_in_input")
    output = models.ManyToManyField(PathType, related_name="pathtype_in_output")

    def __str__(self):
        return "pipe %s using %s" % (self.name, self.software.name)


class PipeInPlan(models.Model):
    """
    The pipes executed in a plan.
    """

    name = models.CharField(max_length=32, default="vol001")
    plan = models.ForeignKey(ProcPlan, on_delete=models.CASCADE)
    step = models.PositiveSmallIntegerField(default=1)
    pipe = models.ForeignKey(Pipe, on_delete=models.CASCADE)

    def __str__(self):
        return "[%s] %s" % (self.plan, self.pipe)

    def get_replacement_map(self, proc_run=None, msi_session=None):
        mapping = {
            "proc_plan": self.plan.name,
            "pipe": self.pipe.name,
        }
        if proc_run:
            mapping["proc_run"] = proc_run.name
            mapping["proc_software"] = self.pipe.software.dirname
            mapping["workflow"] = mapping["proc_software"]  # Legacy alias
        if msi_session:
            mapping["msi_session"] = msi_session.name
            mapping["scope"] = msi_session.session_plan.scope.name
        return mapping


class PipeJoint(models.Model):
    """
    Joint to connect a pipe needing input with an output static path of another pipe.
    This format allows multiple single direction inputs to be defined on pipes.
    """

    pipe_in_plan = models.ForeignKey(
        PipeInPlan,
        related_name="plan_of_pipe",
        on_delete=models.CASCADE,
        help_text="Relates where the pipt is that needing input is in its plan",
    )
    input_pipe_in_plan = models.ForeignKey(
        PipeInPlan,
        related_name="plan_of_input_pipe",
        on_delete=models.CASCADE,
        help_text="Relates where the pipe is used as input is in its plan",
    )
    input_pathtype = models.ForeignKey(
        PathType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="The output pathtype from input_pipe used as the input",
    )

    def __str__(self):
        return "%s needs %s from %s" % (
            self.pipe_in_plan,
            self.input_pathtype.data_kind.data_type,
            self.input_pipe_in_plan,
        )


# record
class ProcRun(models.Model):
    """
    A single execution of a processing plan. It gives a json file describing the
    options used.  All output are saved under the rundir.
    """

    name = models.CharField(max_length=20, default="run001")
    proc_plan = models.ForeignKey(ProcPlan, on_delete=models.CASCADE)
    msi_session = models.ForeignKey(MsiSession, on_delete=models.CASCADE)
    notes = models.TextField(max_length=255, blank=True, null=True)
    json_path = models.ForeignKey(Path, on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "%s-%s" % (self.proc_plan, self.name)

    def save_pipe_run_data(self):
        """
        Creation of ProcRun instance triggers saving of pipe_run_data which are
        output data of the run.

        Delegates to PipelineDataService for actual implementation.
        """
        from processes.services import PipelineDataService

        return PipelineDataService.save_pipe_run_data(self)

    def create_frames_runpipedata(self, msi_session):
        """Delegates to RunCreationService."""
        from processes.services import RunCreationService

        return RunCreationService.create_frames_runpipedata(self, msi_session)

    def _get_pipe_joints(self, pipe):
        """Delegates to RunCreationService."""
        from processes.services import RunCreationService

        return RunCreationService.get_pipe_joints(pipe)

    def _get_input_pipe_pks(self, pipe):
        """Delegates to RunCreationService."""
        from processes.services import RunCreationService

        return RunCreationService.get_input_pipe_pks(self, pipe)

    def create_tomogram_collection(self, input_objects={}):
        """
        Save data-portal schema-like record. Return True if the run adds data to these records.

        Delegates to RunCreationService for actual implementation.
        """
        from processes.services import RunCreationService

        return RunCreationService.create_tomogram_collection(self, input_objects)

    def _add_other_objects(self, class_name, my_rpdata, input_pipe_pks):
        """Delegates to RunCreationService."""
        from processes.services import RunCreationService

        return RunCreationService.add_other_objects(self, class_name, my_rpdata, input_pipe_pks)

    def is_recon_ctf_deconvolved(self, pipe):
        """Delegates to RunCreationService."""
        from processes.services import RunCreationService

        return RunCreationService.is_recon_ctf_deconvolved(self, pipe)

    def _get_tomo_pipe(self, pipe_joints):
        """Delegates to RunCreationService."""
        from processes.services import RunCreationService

        return RunCreationService.get_tomo_pipe(pipe_joints)

    def _save_instance(self, pdata, input_pipe_pks, input_objects={}):
        """Delegates to RunCreationService."""
        from processes.services import RunCreationService

        return RunCreationService.save_instance(self, pdata, input_pipe_pks, input_objects)

    def _get_pipe_range(self, all_input_pipe_pks, my_pipe, input_objects):
        """Delegates to RunCreationService."""
        from processes.services import RunCreationService

        return RunCreationService.get_pipe_range(self, all_input_pipe_pks, my_pipe, input_objects)


class RunPipeData(models.Model):
    """
    Output data path record of the processing run
    """

    run = models.ForeignKey(ProcRun, on_delete=models.CASCADE)
    pipe = models.ForeignKey(Pipe, on_delete=models.CASCADE)
    path = models.ForeignKey(Path, on_delete=models.CASCADE, null=True)
    pathtype = models.ForeignKey(PathType, on_delete=models.CASCADE)

    def __str__(self):
        return "%s %s: %s" % (self.run, self.pipe.name, self.path)


class PipeExecution(models.Model):
    """
    Tracks execution of a single pipe within a processing run.

    This model records the lifecycle of a pipeline step execution:
    - When it was submitted to SLURM
    - What job ID was assigned
    - What parameters were used
    - Current status (pending, submitted, running, completed, failed)
    - When it started and completed

    Enables:
    - Per-step execution tracking
    - Manual step-by-step pipeline execution
    - Retry of failed steps
    - Parameter history
    """

    proc_run = models.ForeignKey(ProcRun, on_delete=models.CASCADE, related_name="pipe_executions")
    pipe_in_plan = models.ForeignKey(PipeInPlan, on_delete=models.CASCADE)

    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("submitted", "Submitted"),
            ("running", "Running"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="pending",
        db_index=True,
    )

    # SLURM job information
    job_id = models.CharField(max_length=32, null=True, blank=True, db_index=True)
    script_path = models.CharField(max_length=512, null=True, blank=True)
    script_content = models.TextField(null=True, blank=True)  # Full rendered SLURM script

    # Parameters used for this execution (JSON)
    parameters = models.JSONField(default=dict)

    # Timestamps
    submitted_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Error tracking
    error_message = models.TextField(null=True, blank=True)

    # Syncer tracking
    syncer_active = models.BooleanField(
        default=False, help_text="Whether a JobStatusSyncer is actively monitoring this job"
    )

    # Job execution logs (stdout/stderr from SLURM)
    stdout_log = models.TextField(
        null=True, blank=True, help_text="Standard output log content from SLURM job (max ~1MB)"
    )
    stderr_log = models.TextField(
        null=True, blank=True, help_text="Standard error log content from SLURM job (max ~1MB)"
    )
    logs_fetched_at = models.DateTimeField(
        null=True, blank=True, help_text="Timestamp when logs were fetched from cluster"
    )
    log_fetch_error = models.TextField(null=True, blank=True, help_text="Error message if log fetching failed")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["pipe_in_plan__step"]
        unique_together = [["proc_run", "pipe_in_plan"]]

    def __str__(self):
        return f"{self.proc_run} - {self.pipe_in_plan.pipe.name} ({self.status})"


class SyncerLog(models.Model):
    """
    Log entries for syncer actions.

    Tracks syncer activity including initialization, file discoveries,
    tomogram creation/deletion, and errors. Used to display syncer progress
    in the job logs modal.
    """

    ACTION_TYPE_CHOICES = [
        ("init", "Initialization"),
        ("sync_start", "Sync Started"),
        ("sync_complete", "Sync Completed"),
        ("file_found", "File Found"),
        ("tomogram_created", "Tomogram Created"),
        ("tomogram_deleted", "Tomogram Deleted"),
        ("review_updated", "Review Updated"),
        ("job_check", "Job Status Check"),
        ("error", "Error"),
        ("warning", "Warning"),
        ("stopped", "Syncer Stopped"),
    ]

    # Link to the job execution
    pipe_execution = models.ForeignKey(
        PipeExecution,
        on_delete=models.CASCADE,
        related_name="syncer_logs",
        null=True,
        blank=True,
        help_text="PipeExecution this log belongs to",
    )

    # Alternative: link by job_id for legacy syncers
    job_id = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        db_index=True,
        help_text="SLURM job ID (for legacy syncers without PipeExecution)",
    )

    # Log details
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    action_type = models.CharField(max_length=20, choices=ACTION_TYPE_CHOICES, db_index=True)
    message = models.TextField(help_text="Human-readable log message")

    # Structured metadata (JSON) for additional context
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional structured data (e.g., file paths, counts, error details)",
    )

    # Syncer identification
    syncer_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Syncer class name (e.g., AretomoSyncer, DenoiseSyncer)",
    )
    session_name = models.CharField(max_length=100, null=True, blank=True)
    run_id = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["pipe_execution", "-timestamp"]),
            models.Index(fields=["job_id", "-timestamp"]),
            models.Index(fields=["session_name", "run_id", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.action_type}: {self.message[:50]}..."


class SyncerProcess(models.Model):
    """
    Tracks the status of running syncer processes.

    Used to determine if a syncer needs to be re-run (stopped unexpectedly).
    When a syncer starts, a SyncerProcess record is created. The syncer updates
    the last_heartbeat field periodically. If the job is still running but the
    syncer has stopped (no recent heartbeat), the syncer can be re-run.
    """

    STATUS_CHOICES = [
        ("running", "Running"),
        ("stopped", "Stopped"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    # Link to job
    pipe_execution = models.OneToOneField(
        PipeExecution,
        on_delete=models.CASCADE,
        related_name="syncer_process",
        null=True,
        blank=True,
    )
    job_id = models.CharField(max_length=32, null=True, blank=True, db_index=True)

    # Syncer identification
    syncer_type = models.CharField(max_length=50)

    # Session/run info for re-running
    session_name = models.CharField(max_length=100)
    run_id = models.CharField(max_length=50)

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="running")
    started_at = models.DateTimeField(auto_now_add=True)
    last_heartbeat = models.DateTimeField(auto_now=True)
    stopped_at = models.DateTimeField(null=True, blank=True)

    # Django-Q task tracking
    task_id = models.CharField(max_length=100, null=True, blank=True)

    # Error info
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["job_id"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.syncer_type} for job {self.job_id} ({self.status})"

    def is_unexpectedly_stopped(self) -> bool:
        """
        Check if syncer stopped unexpectedly (job still running but syncer is not).
        """
        if self.status != "stopped":
            return False

        # Check if the associated job is still running
        if self.pipe_execution:
            return self.pipe_execution.status in ["submitted", "running"]
        return False


# models to record the final relationship. Path should have everything except tomo_run
class TiltAngles(models.Model):
    pipe_data = models.ForeignKey(RunPipeData, on_delete=models.CASCADE)
    msi_session = models.ForeignKey(MsiSession, on_delete=models.CASCADE)  # included here for easy query


class Frames(models.Model):
    session_plan = models.ForeignKey(SessionPlan, on_delete=models.CASCADE)
    msi_session = models.ForeignKey(
        MsiSession, on_delete=models.CASCADE, related_name="session_of_frames"
    )  # included here for easy query
    frame_path = models.ForeignKey(Path, related_name="processing_frame_path", on_delete=models.CASCADE)

    def __str__(self):
        return "%s" % (self.frame_path)


class RawTiltSeries(models.Model):
    pipe_data = models.ForeignKey(RunPipeData, on_delete=models.CASCADE)
    msi_session = models.ForeignKey(MsiSession, on_delete=models.CASCADE)  # included here for easy query
    angles = models.ForeignKey(TiltAngles, on_delete=models.CASCADE)
    frames = models.ForeignKey(Frames, on_delete=models.CASCADE)

    def __str__(self):
        return "%s" % (self.pipe_data)


class Ctf(models.Model):
    pipe_data = models.ForeignKey(RunPipeData, on_delete=models.CASCADE)
    msi_session = models.ForeignKey(MsiSession, on_delete=models.CASCADE)  # included here for easy query
    tiltseries = models.ForeignKey(RawTiltSeries, on_delete=models.CASCADE)

    def __str__(self):
        return "%s" % (self.pipe_data)


class Alignment(models.Model):
    pipe_data = models.ForeignKey(RunPipeData, on_delete=models.CASCADE)
    msi_session = models.ForeignKey(MsiSession, on_delete=models.CASCADE)  # included here for easy query
    tiltseries = models.ForeignKey(RawTiltSeries, on_delete=models.CASCADE)

    def __str__(self):
        return "%s" % (self.pipe_data)


class TomogramVoxelSpacing(models.Model):
    spacing = models.FloatField(default=10.0, help_text="uniform voxel spacing in angstroms")

    def __str__(self):
        return "%.3f" % (self.spacing)


class ReconMethod(models.Model):
    """
    Processing Method that creates tomogram from alignment
    """

    name = models.CharField(max_length=32, default="weighted back projection")

    def __str__(self):
        return "%s" % (self.name)


class TomoPostProcessMethod(models.Model):
    """
    Processing Method that converts one tomogram into another through filtering, denoising etc.
    """

    name = models.CharField(max_length=32, default="denoised")
    software = models.ForeignKey(ProcSoftware, on_delete=models.CASCADE)

    class Meta:
        unique_together = [["name", "software"]]

    def __str__(self):
        return "%s by %s" % (self.name, self.software)


class Tomograms(models.Model):
    """
    Tomogram collection within the msi_session
    """

    # This allows denoise or other type of tomograms to be included
    pipe_data = models.ForeignKey(RunPipeData, on_delete=models.CASCADE)
    recon_method = models.ForeignKey(ReconMethod, on_delete=models.CASCADE)
    voxel_spacing = models.ForeignKey(TomogramVoxelSpacing, on_delete=models.CASCADE)
    alignment = models.ForeignKey(Alignment, on_delete=models.CASCADE)
    ctf = models.ForeignKey(Ctf, on_delete=models.CASCADE, null=True, blank=True)
    msi_session = models.ForeignKey(MsiSession, on_delete=models.CASCADE)  # included here for easy query
    post_process = models.ForeignKey(TomoPostProcessMethod, on_delete=models.SET_NULL, null=True, blank=True)
    parent_tomo = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return "tomo @ %s" % (self.pipe_data)


class AnnotationMethod(models.Model):
    name = models.CharField(max_length=32, default="template matching")

    def __str__(self):
        return "%s" % (self.name)


class Annotation(models.Model):
    pipe_data = models.ForeignKey(RunPipeData, on_delete=models.CASCADE)
    msi_session = models.ForeignKey(MsiSession, on_delete=models.CASCADE)  # included here for easy query
    tomograms = models.ForeignKey(Tomograms, on_delete=models.CASCADE)
    name = models.CharField(max_length=32, default="ribosome")
    ontology_term = models.CharField(max_length=20, default="GO:0005840")
    annotation_type = models.CharField(max_length=12, default="point")
    annotation_method = models.ForeignKey(AnnotationMethod, on_delete=models.CASCADE)
    parent_anno = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True)
    notes = models.TextField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "%s" % (self.pipe_data)


class ParticleGallery(models.Model):
    pipe_data = models.ForeignKey(RunPipeData, on_delete=models.CASCADE)
    msi_session = models.ForeignKey(MsiSession, on_delete=models.CASCADE)  # included here for easy query
    tomograms = models.ForeignKey(Tomograms, on_delete=models.CASCADE)
    pick = models.ForeignKey(Annotation, on_delete=models.CASCADE)

    def __str__(self):
        return "%s" % (self.pipe_data)


def suggest_name(prefix, msi_session, plan, model_name="ProcRun"):
    """
    Make unique name by advancing to next integer.
    """
    model_instance = getattr(sys.modules[__name__], model_name)
    if prefix:
        prefix_search = prefix
        old_runs = model_instance.objects.filter(
            Q(name__startswith=prefix_search), proc_plan=plan, msi_session=msi_session
        )
        used_names = list(map((lambda x: x.name), old_runs))
        if not used_names:
            # first session of the day
            return prefix_search + "%03d" % 1
        used_numbers = list(map((lambda x: int(x.split(prefix_search)[-1])), used_names))
        return "%s%03d" % (prefix, max(used_numbers) + 1)
    else:
        raise ValueError("Prefix must not be empty string for run name")


def select_plan_ids_by_input_data_types(selected_data_types):
    selected_kinds = DataKind.objects.filter(data_type__in=selected_data_types)
    selected_pipes = Pipe.objects.filter(input__in=selected_kinds)
    pipe_in_plans = PipeInPlan.objects.filter(pipe__in=selected_pipes)
    plan_ids = list(map((lambda x: x.plan.id), pipe_in_plans))
    return plan_ids


class JobLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    job_name = models.CharField(max_length=150, null=True, blank=True)
    advanced = models.BooleanField(default=False)
    job_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(default=now)

    # <-- Add a JSONField to store all job parameters
    parameters = models.JSONField(null=True, blank=True)

    # Optionally store any error messages
    error_message = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Aretomo Job {self.job_id} by {self.user.username}"


class Review(models.Model):
    """
    A review record for an MSI session, containing review metadata and status.
    """

    review_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review_name = models.CharField(max_length=255)
    review_type = models.CharField(max_length=100)
    run_id = models.CharField(max_length=100)
    reconstruction_type = models.CharField(max_length=100)
    total_count = models.IntegerField(default=0)
    reviewed_count = models.IntegerField(default=0)
    status = models.CharField(max_length=32, default="pending")  # pending, in_progress, completed, rejected
    save_path = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    msi_session = models.ForeignKey(MsiSession, on_delete=models.CASCADE, related_name="raw_tomograms")
    requestor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="requested_reviews")
    objects_of_interest = models.TextField(null=True)
    cluster = models.ForeignKey(
        Cluster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews",
    )

    def __str__(self):
        return f"Review {self.review_name} for {self.msi_session.name}"


class ReviewTomogram(models.Model):
    """
    A tomogram review record, linking specific tomograms to a review.
    """

    tomogram_id = models.CharField(max_length=100, primary_key=True)

    session = models.ForeignKey(
        MsiSession, on_delete=models.CASCADE, related_name="review_tomograms", null=True, blank=True
    )
    review = models.ForeignKey(
        Review, on_delete=models.SET_NULL, null=True, blank=True, related_name="review_tomograms"
    )

    run_id = models.CharField(max_length=100, null=True, blank=True)  # e.g., UUID or filename-based ID
    reconstruction_type = models.CharField(max_length=100, null=True, blank=True)  # e.g., 'WBP', 'SIRT', 'SGD'

    position_id = models.CharField(max_length=100)
    file_path = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="discovered file path relative to the run directory",
    )
    quality = models.CharField(
        max_length=20,
        choices=[
            ("", ""),
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
            ("uncertain", "Uncertain"),
        ],
        default="pending",
    )
    rejection_reasons = models.JSONField(default=list, blank=True)
    object_labels = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["review", "tomogram_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "run_id", "reconstruction_type", "position_id"],
                name="uniq_reviewtomogram_identity",
            ),
        ]

    def __str__(self):
        return f"Tomogram Review {self.tomogram_id} in {self.review}"


class FilesystemSurvey(models.Model):
    """
    Tracks a SLURM-submitted filesystem survey job that discovers all files on a cluster.

    Surveys produce a Parquet file on the cluster containing file-level details
    (path, size, mtime, uid, mode, type). The Django DB stores only survey metadata
    and directory-level aggregates (via DirectorySummary) to avoid bloating the database.
    """

    CLUSTER_CHOICES = [
        ("czii", "CZII"),
        ("bruno", "Bruno"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("submitted", "Submitted"),
        ("running", "Running"),
        ("processing", "Processing Results"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    # Survey identification
    cluster = models.CharField(max_length=16, choices=CLUSTER_CHOICES, db_index=True)
    base_path = models.CharField(max_length=500, help_text="Root path that was surveyed")

    # SLURM job tracking
    job_id = models.CharField(max_length=32, null=True, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)

    # External file storage (Parquet file on cluster)
    results_parquet_path = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Path to Parquet file on cluster containing file-level details",
    )

    # Aggregate statistics (computed during post-processing)
    total_files = models.BigIntegerField(default=0)
    total_directories = models.BigIntegerField(default=0)
    total_size_bytes = models.BigIntegerField(default=0)

    # By-user aggregates (stored as JSON to avoid many rows)
    size_by_user = models.JSONField(default=dict, blank=True, help_text='{"username": bytes, ...}')
    count_by_user = models.JSONField(default=dict, blank=True, help_text='{"username": file_count, ...}')

    # By-origin aggregates
    size_by_origin = models.JSONField(default=dict, blank=True, help_text='{"app_generated": bytes, ...}')
    count_by_origin = models.JSONField(default=dict, blank=True, help_text='{"app_generated": file_count, ...}')

    # Timestamps
    submitted_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Error tracking
    error_message = models.TextField(null=True, blank=True)

    # Created by
    submitted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_surveys",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["cluster", "status"]),
            models.Index(fields=["cluster", "-created_at"]),
        ]

    def __str__(self):
        return f"Survey {self.id} on {self.cluster} ({self.status})"

    def get_size_display(self):
        """Return human-readable total size"""
        size = self.total_size_bytes
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"


class DirectorySummary(models.Model):
    """
    Directory-level aggregates stored in DB for fast querying.

    One row per directory path per survey. This allows the UI to browse directories
    without reading the full Parquet file. File-level details can be fetched
    on-demand by querying the Parquet file via DuckDB.
    """

    ORIGIN_CHOICES = [
        ("app_generated", "App Generated"),
        ("synced_from_czii", "Synced from CZII"),
        ("user_created", "User Created"),
        ("unknown", "Unknown"),
    ]

    PRESERVE_STATUS_CHOICES = [
        ("unset", "Unset"),
        ("preserve", "Preserve"),
        ("delete", "Delete"),
        ("review", "Needs Review"),
    ]

    # Link to survey
    survey = models.ForeignKey(
        FilesystemSurvey,
        on_delete=models.CASCADE,
        related_name="directory_summaries",
    )
    cluster = models.CharField(max_length=16, db_index=True)
    path = models.CharField(max_length=500, help_text="Directory path")

    # Aggregates
    file_count = models.IntegerField(default=0)
    total_size_bytes = models.BigIntegerField(default=0)
    owner_username = models.CharField(max_length=64, null=True, blank=True, help_text="Most common owner")
    owner_uid = models.IntegerField(null=True, blank=True)

    # Origin (computed from path matching domain entities or survey comparison)
    origin = models.CharField(max_length=20, choices=ORIGIN_CHOICES, default="unknown", db_index=True)

    # Linked content (if this directory matches a known domain entity path)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    # Preservation status (user decisions)
    preserve_status = models.CharField(
        max_length=20,
        choices=PRESERVE_STATUS_CHOICES,
        default="unset",
        db_index=True,
    )
    status_updated_at = models.DateTimeField(null=True, blank=True)
    status_updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="directory_status_updates",
    )
    status_notes = models.TextField(null=True, blank=True)

    # Depth (for hierarchical queries)
    depth = models.IntegerField(default=0, help_text="Directory depth from base_path")

    # Timestamps from filesystem
    newest_file_mtime = models.DateTimeField(null=True, blank=True)
    oldest_file_mtime = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["survey", "path"]
        indexes = [
            models.Index(fields=["cluster", "origin", "preserve_status"]),
            models.Index(fields=["survey", "depth"]),
            models.Index(fields=["cluster", "path"]),
            models.Index(fields=["owner_username"]),
        ]
        ordering = ["path"]

    def __str__(self):
        return f"{self.path} ({self.file_count} files, {self.get_size_display()})"

    def get_size_display(self):
        """Return human-readable total size"""
        size = self.total_size_bytes
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"


def format_bytes(size):
    """Human-readable byte count, matching DirectorySummary.get_size_display()."""
    size = float(size or 0)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def current_survey(cluster):
    """
    The survey whose tree represents the latest completed scan for a cluster
    """
    return FilesystemSurvey.objects.filter(cluster=cluster, status="completed").order_by("-completed_at", "-id").first()


class StorageRunSummaryQuerySet(models.QuerySet):
    def current(self, cluster):
        """
        Leaves for the newest completed survey on one cluster.

        Returns an empty queryset when the cluster has no completed survey.
        """
        survey = current_survey(cluster)
        if survey is None:
            return self.none()
        return self.filter(survey=survey)


class StorageRunSummary(models.Model):
    """
    Materialized leaf of the storage tree: one row per
    (survey, software, session, run) directory group.

    Built by processes.services.storage_tree.build_storage_tree(). Every field
    is derived, so the table can be dropped and rebuilt at any time.

    scope reads by survey; `objects.current(cluster)` is the intended usage

    Decisions live in StorageDecision
    """

    objects = StorageRunSummaryQuerySet.as_manager()

    survey = models.ForeignKey(
        FilesystemSurvey,
        on_delete=models.CASCADE,
        related_name="run_summaries",
    )
    cluster = models.CharField(max_length=16, db_index=True)

    # Path-derived identity, relative to survey.base_path.
    software = models.CharField(max_length=64, db_index=True, help_text="Depth-1 segment, e.g. 'aretomo3'")
    session_name = models.CharField(
        max_length=255, db_index=True, help_text="Depth-2 segment; may not be a known MsiSession"
    )
    run_name = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Depth-3 segment. Empty means files directly under the session directory.",
    )
    path_prefix = models.CharField(max_length=512, help_text="The directory this leaf covers")

    # Resolved links. NULL means "on disk, but Embrella has no record of it".
    # SET_NULL throughout: deleting a record must not erase the survey's
    # evidence that the bytes are still on the cluster.
    msi_session = models.ForeignKey(
        MsiSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="storage_run_summaries",
    )
    proc_run = models.ForeignKey(
        "processes.ProcRun",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="storage_run_summaries",
    )
    proc_software = models.ForeignKey(
        "processes.ProcSoftware",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="storage_run_summaries",
    )

    # Rollups over every descendant DirectorySummary row.
    directory_count = models.IntegerField(default=0)
    file_count = models.BigIntegerField(default=0)
    total_size_bytes = models.BigIntegerField(default=0)
    newest_file_mtime = models.DateTimeField(null=True, blank=True)
    oldest_file_mtime = models.DateTimeField(null=True, blank=True)
    owner_username = models.CharField(max_length=64, blank=True, default="", help_text="Most common owner")

    built_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["survey", "software", "session_name", "run_name"]
        indexes = [
            models.Index(fields=["survey", "session_name"]),
            models.Index(fields=["survey", "software"]),
            models.Index(fields=["survey", "-total_size_bytes"]),
        ]
        ordering = ["session_name", "software", "run_name"]
        verbose_name_plural = "storage run summaries"

    def __str__(self):
        run = self.run_name or "(session root)"
        return f"{self.software}/{self.session_name}/{run} ({self.get_size_display()})"

    @property
    def registered(self):
        """True when the path's session name resolves to a real MsiSession."""
        return self.msi_session_id is not None

    def get_size_display(self):
        return format_bytes(self.total_size_bytes)


class StorageDecision(models.Model):
    """
    A preservation decision about a directory, keyed on the path

    One row per decision, not per affected directory -- marking a session
    writes a single row whose prefix covers every descendant.
    Cascades with longest matching prefix, so a run-level decision overrides
    session-level parent (bad older run, but newer ones can be preserved).

    NOTE: Currently does not handle delete, move or modify files
    """

    cluster = models.CharField(max_length=16, db_index=True)
    path_prefix = models.CharField(max_length=512, help_text="Session or run directory this decision covers")
    status = models.CharField(max_length=20, choices=DirectorySummary.PRESERVE_STATUS_CHOICES)
    notes = models.TextField(blank=True, default="")
    decided_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="storage_decisions",
    )
    decided_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["cluster", "path_prefix"]
        indexes = [models.Index(fields=["cluster", "path_prefix"])]
        ordering = ["cluster", "path_prefix"]

    def __str__(self):
        return f"{self.get_status_display()}: {self.path_prefix}"
