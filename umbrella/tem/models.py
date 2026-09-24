import string
import sys
import time

from cryo_grids.models import CryoGrid, CryoGridCassette
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, validate_comma_separated_integer_list
from django.db import models
from django.db.models import Q
from django.utils import timezone
from projects.models import Project
from stores.models import FilePattern, Path, PathType, fill_place_holders
from stores.paths import assert_fully_resolved

from common.sorting import NAME_PREFIX_RE

TEM_CHOICES = {
    "imaging_mode": [
        ("tem", "TEM"),
        ("stem", "STEM"),
    ],
    "workflow": [
        ("scrn", "Grid Screening"),
        ("sngl", "Single Tilt SPA"),
        ("tomo", "Tomography"),
        ("ptyc", "Ptychography"),
        ("idpc", "iDPC"),
        ("clem", "CLEM Mapping"),
    ],
}

# This determines file structure
TEM_COLLECTION_SOFTWARE = [
    ("epu", "TFS EPU"),
    ("ser", "SerialEM"),
    ("tom5", "TFS Tomo5"),
    ("legn", "Leginon"),
]


class Microscope(models.Model):
    """
    Microscope determines what camera is available.
    """

    name = models.CharField(max_length=20, default="Krios1", unique=True)
    cs = models.FloatField(default=2.7, help_text="Spherical abberation constant in mm")
    manufacturer = models.CharField(max_length=256, blank=True, default="")
    model = models.CharField(max_length=256, blank=True, default="")
    energy_filter = models.CharField(max_length=256, blank=True, default="")
    phase_plate = models.CharField(max_length=256, blank=True, default="")
    image_correctors = models.JSONField(default=list, blank=True, help_text='e.g. ["Cs corrector", "Cc corrector"]')

    def __str__(self):
        return self.name

    class Meta:
        app_label = "tem"


class Camera(models.Model):
    """
    Camera determines the path where frames are saved.
    """

    name = models.CharField(max_length=20, default="Falcon4i", unique=True)
    manufacturer = models.CharField(max_length=256, blank=True, default="")
    model = models.CharField(max_length=256, blank=True, default="")
    root_dir = models.CharField(max_length=80, unique=True)
    frame_format = models.CharField(max_length=20)
    initial_frame_base_dir = models.CharField(max_length=20)
    gain = models.ForeignKey(
        PathType,
        related_name="gain_type",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="path pattern to the gain reference files this camera writes",
    )

    def __str__(self):
        return self.name

    @property
    def role_path_types(self):
        """role -> its default template, None where this camera writes no such data."""
        return {role: getattr(self, role) for role in CAMERA_PATH_ROLES}

    class Meta:
        app_label = "tem"


class Magnification(models.Model):
    """
    Uniquely identify a magnification. This is used to propogate selection list sorted by the index.
    """

    scope = models.ForeignKey(Microscope, on_delete=models.CASCADE)
    mode = models.CharField(max_length=8, default="SA", help_text="projection mode")
    nominal_mag = models.PositiveIntegerField(default=50000, help_text="Nominal mag displayed on the scope")
    index = models.PositiveIntegerField(default=0, help_text="Base 0 index of list order")

    def __str__(self):
        return "%gkx (%s) (%s)" % (self.nominal_mag / 1000, self.mode, self.scope)

    class Meta:
        app_label = "tem"
        unique_together = [["scope", "mode", "nominal_mag"]]


class CalibratedPixelSize(models.Model):
    mag = models.ForeignKey(Magnification, on_delete=models.CASCADE)
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE)
    pixel_spacing = models.FloatField(default=4.0, help_text="Pixel spacing in Angstroms")
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    calibrated_at = models.DateTimeField(help_text="When the calibration was performed", null=True, blank=True)

    def __str__(self):
        cal_date = self.calibrated_at.strftime("%y%b%d") if self.calibrated_at else "no cal date"
        return "%s@%d-%s: %.3f Å/pixel (%s)" % (
            self.mag.scope,
            self.mag.nominal_mag,
            self.camera,
            self.pixel_spacing,
            cal_date,
        )

    class Meta:
        app_label = "tem"


SOFTWARE_PATH_ROLES = ("frames", "sums", "mdocs", "parents", "atlas")
# `atlas` is inherited from the grid's screening session instead. See MsiSession.resolve_role_paths.
INHERITED_ROLE = "atlas"
RESOLVED_ROLES = tuple(role for role in SOFTWARE_PATH_ROLES if role != INHERITED_ROLE)

# The plan's tilt-series stack naming
TILT_SERIES_ROLE = "tilt_series"

# Gain depends on the camera, not the acquisition software: Falcon4i writes .gain files
# into a shared folder, GatanCeltic writes one .dm4 beside the session's frames.
GAIN_ROLE = "gain"
CAMERA_PATH_ROLES = (GAIN_ROLE,)

BINDING_ROLES = SOFTWARE_PATH_ROLES + (TILT_SERIES_ROLE,) + CAMERA_PATH_ROLES

# Which plan member holds a role's default template. Binding-only roles (tilt_series) have none.
#
#   plan.software ── frames, sums, mdocs, parents, atlas
#   plan.camera   ── gain
ROLE_OWNERS = dict.fromkeys(SOFTWARE_PATH_ROLES, "software") | dict.fromkeys(CAMERA_PATH_ROLES, "camera")


class Software(models.Model):
    """
    Software determines the paths of the output files
    """

    name = models.CharField(max_length=50)
    version = models.CharField(
        max_length=32,
        blank=True,
        default="",
        help_text="A version that lays files out differently is a separate row. So is a "
        "distinct protocol -- name it compoundly, e.g. 'Tomo5 dose-symmetric'.",
    )
    frames = models.ForeignKey(
        PathType,
        related_name="frames_type",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="path pattern to access frames",
    )
    sums = models.ForeignKey(
        PathType,
        related_name="sums_type",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="path pattern to access 0 tilt projection thumbnail image",
    )
    mdocs = models.ForeignKey(
        PathType,
        related_name="mdocs_type",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="path pattern to access mdocs",
    )

    parents = models.ForeignKey(
        PathType,
        related_name="parents_type",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="path pattern to access parent images for viewing",
    )
    atlas = models.ForeignKey(
        PathType,
        related_name="atlas_type",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="path pattern to access grid atlas image for viewing",
    )

    def __str__(self):
        return "%s %s" % (self.name, self.version) if self.version else self.name

    @property
    def role_path_types(self):
        """role -> its default template, None where this software emits no such data."""
        return {role: getattr(self, role) for role in SOFTWARE_PATH_ROLES}

    class Meta:
        app_label = "tem"
        unique_together = [["name", "version"]]


class ImagingWorkflow(models.Model):
    imaging_mode = models.CharField(max_length=20, choices=TEM_CHOICES["imaging_mode"])
    workflow = models.CharField(max_length=20, choices=TEM_CHOICES["workflow"])

    def __str__(self):
        return "%s %s" % (self.get_imaging_mode_display(), self.get_workflow_display())


# Accessory acquisition parameters. Adding one: a column below, and its name here.
ACQUISITION_FIELDS = ("super_resolution",)


class AcquisitionSettings(models.Model):
    """Accessory acquisition parameters that vary per setup, not per software.

    One table, used for: session plan defaults for acquisition settings, and snapshots by msi sessions
    """

    label = models.CharField(
        max_length=40, blank=True, default="", help_text="Names a plan profile. Blank on snapshots."
    )
    super_resolution = models.BooleanField(
        default=False,
        help_text="Camera wrote super-resolution frames: frame pixel size is half the calibrated one.",
    )

    class Meta:
        app_label = "tem"
        verbose_name_plural = "acquisition settings"

    def values(self):
        return {field: getattr(self, field) for field in ACQUISITION_FIELDS}

    def snapshot(self, label, **overrides):
        """A new, saved copy named `label` with `overrides` applied. Never shares a row with the profile."""
        return AcquisitionSettings.objects.create(label=label, **{**self.values(), **overrides})

    @staticmethod
    def snapshot_label(session_name):
        """How a session's snapshot reads in the admin list, e.g. "snapshot p26sep14a"."""
        return "snapshot %s" % session_name

    def __str__(self):
        return self.label or "snapshot %s" % self.pk


class SessionPlan(models.Model):
    scope = models.ForeignKey(Microscope, on_delete=models.CASCADE)
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE)
    imaging_workflow = models.ForeignKey(ImagingWorkflow, on_delete=models.CASCADE)
    software = models.ForeignKey(Software, on_delete=models.CASCADE)
    acquisition_defaults = models.ForeignKey(
        AcquisitionSettings,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="plans",
        help_text="Profile copied into each new session; the operator may override at create time.",
    )
    name_prefix = models.CharField(
        max_length=4,
        blank=True,
        default="",
        validators=[RegexValidator(NAME_PREFIX_RE, "Lowercase letters only.")],
        help_text="Lowercase letters put in front of suggested MSI session names, so sessions from "
        "this scope/software pair are told apart at a glance. Blank for none. "
        "E.g. 's' suggests s26jun08a; blank suggests 26jun08a.",
    )

    def acquisition_values(self):
        """The profile's values, or the field defaults when the plan has no profile."""
        return (self.acquisition_defaults or AcquisitionSettings()).values()

    def __str__(self):
        return "%s collected with %s on %s and %s" % (self.imaging_workflow, self.software, self.scope, self.camera)

    class Meta:
        app_label = "tem"


class SessionPlanPathBinding(models.Model):
    """Per-plan override of which template a role resolves to.

    Directory and filename override independently: a scope writing into the shared directory
    under its own naming convention sets `file_pattern` alone, with no duplicate PathType row.
    """

    session_plan = models.ForeignKey(SessionPlan, related_name="path_bindings", on_delete=models.CASCADE)
    role = models.CharField(max_length=16, choices=[(r, r) for r in BINDING_ROLES])
    path_type = models.ForeignKey(
        PathType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Directory template for this role on this plan. Blank falls back to the software default.",
    )
    file_pattern = models.ForeignKey(
        FilePattern,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Filename convention for this role on this plan. Blank falls back to the resolved directory's own.",
    )
    is_active = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        app_label = "tem"
        unique_together = [["session_plan", "role"]]

    def __str__(self):
        return "%s/%s -> %s" % (self.session_plan_id, self.role, self.path_type or "(default)")


def _active_binding(plan, role):
    return plan.path_bindings.filter(role=role, is_active=True).first()


def _role_default(plan, role):
    """The owner's template for `role` (see ROLE_OWNERS), None for binding-only roles."""
    owner = ROLE_OWNERS.get(role)
    if owner is None:
        return None
    return getattr(plan, owner).role_path_types[role]


def resolve_role_path_type(plan, role):
    """The PathType for `role` on `plan`: binding first, then the role owner's default --
    Software for acquisition roles, Camera for gain.

    Returns None when the owner does not emit this role at all -- a terminal answer,
    unlike a missing binding, which only means "use the default".
    """
    binding = _active_binding(plan, role)
    if binding and binding.path_type:
        return binding.path_type
    return _role_default(plan, role)


def resolve_plan_file_pattern(plan, role):
    """The plan-bound FilePattern for `role`, or None."""
    binding = _active_binding(plan, role)
    return binding.file_pattern if binding else None


def resolve_role_file_pattern(plan, role):
    """The FilePattern for `role` on `plan`: binding first, then the directory's own."""
    bound = resolve_plan_file_pattern(plan, role)
    if bound:
        return bound

    path_type = resolve_role_path_type(plan, role)
    return path_type.file_pattern if path_type else None


def plan_replacement_map(plan):
    """Placeholder values derivable from a SessionPlan alone.

    Shared by every acquisition template, whether it is resolved from an `MsiSession` or
    an `AtlasSession`; each adds its own identity tokens on top. See
    `stores.placeholders` for the vocabulary this has to satisfy.
    """
    camera = plan.camera
    return {
        "workflow": plan.imaging_workflow.workflow,
        "scope": plan.scope.name,
        "camera": camera.name,
        "frame_format": camera.frame_format,
        "root_dir": camera.root_dir.rstrip("/"),
        "initial_frame_base_dir": camera.initial_frame_base_dir.rstrip("/"),
    }


class ScreenSessionGroup(models.Model):
    """
    A grouping of screening on grids. It is identified by the cassette
    and the order of the grid positions that are loaded and imaged.
    """

    name = models.CharField(max_length=20, unique=True)
    cassette = models.ForeignKey(CryoGridCassette, on_delete=models.PROTECT, null=True)
    session_plan = models.ForeignKey(SessionPlan, on_delete=models.CASCADE)
    order = models.CharField(
        max_length=36,
        validators=[validate_comma_separated_integer_list],
        help_text="comma separated list ofgrid positions to screen, i.e. 1,2,5",
        default="1,2,3,4,5,6,7,8,9,10,11,12",
    )

    def get_order_list(self):
        try:
            return parse_integer_order_list(self.order)
        except Exception as e:
            raise ValueError("Bad order field entry: %s" % e)

    def __str__(self):
        return "%s - Screening of %s" % (self.name, self.cassette)


class AtlasSession(models.Model):
    """
    A tem session which purpose is to assess the quality of the grid.
    Currently only record atlas path.
    """

    # name is determined by software
    name = models.CharField(
        max_length=20, unique=False, help_text="software-dependent name for the screen session for the grid"
    )
    group = models.ForeignKey(ScreenSessionGroup, on_delete=models.CASCADE)
    order_in_screen = models.PositiveSmallIntegerField(default=1)
    grid = models.ForeignKey(CryoGrid, on_delete=models.PROTECT, null=True)
    atlas = models.ForeignKey(Path, related_name="screenatlas", on_delete=models.SET_NULL, null=True)
    quality = models.SmallIntegerField(
        default=-1,
        help_text="grid quality score 0-5 5=highest, -1=not started, 0=failed",
    )
    notes = models.TextField(max_length=255, blank=True, null=True)

    class Meta:
        unique_together = [["name", "group"]]
        constraints = [
            models.CheckConstraint(check=models.Q(quality__lte=5), name="quality_score_exceed_max"),
            models.CheckConstraint(check=models.Q(quality__gte=-1), name="quality_score_not_valid"),
        ]

    def get_replacement_map(self):
        return {
            **plan_replacement_map(self.group.session_plan),
            "session_group": self.group.name,
            "atlas_session": self.name,
        }

    def get_session_dir(self, role=INHERITED_ROLE):
        """The directory `role` resolves to. A screening session only produces its atlas."""
        path_type = resolve_role_path_type(self.group.session_plan, role)
        if not path_type:
            return "."
        return fill_place_holders(
            path_type.overlay_path,
            self.get_replacement_map(),
        )

    def resolve_path_row(self, role=INHERITED_ROLE):
        """The persisted `stores.Path` for `role`, created if this directory has none yet."""
        overlay_path = fill_place_holders(
            self.get_session_dir(role),
            self.get_replacement_map(),
        )
        assert_fully_resolved(overlay_path, describe="%s for atlas session %s" % (role, self.name))
        return Path.first_or_create(overlay_path)

    def __str__(self):
        return "/scrn/%s/%s/" % (self.group.name, self.name)


class MsiSession(models.Model):
    """
    Multi-scale imaging session
    """

    name = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True)
    session_plan = models.ForeignKey(SessionPlan, on_delete=models.CASCADE)
    grid = models.ForeignKey(CryoGrid, on_delete=models.PROTECT, null=True)
    notes = models.TextField(max_length=255, blank=True, null=True)
    frames = models.ForeignKey(Path, related_name="frames", on_delete=models.SET_NULL, null=True, blank=True)
    mdocs = models.ForeignKey(Path, related_name="mdocs", on_delete=models.SET_NULL, null=True, blank=True)
    sums = models.ForeignKey(Path, related_name="sums", on_delete=models.SET_NULL, null=True, blank=True)
    parents = models.ForeignKey(Path, related_name="parents", on_delete=models.SET_NULL, null=True, blank=True)
    atlas = models.ForeignKey(Path, related_name="atlas", on_delete=models.SET_NULL, null=True, blank=True)
    atlas_session = models.ForeignKey(
        AtlasSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="link a seperate grid screen atlas if exists",
    )
    magnification = models.ForeignKey(
        Magnification, on_delete=models.SET_NULL, null=True, blank=True, help_text="Magnification used for this session"
    )
    acquisition = models.OneToOneField(
        AcquisitionSettings,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="session",
        help_text="Snapshot of the plan's acquisition defaults, with the operator's overrides",
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        app_label = "tem"

    def get_replacement_map(self):
        return {
            **plan_replacement_map(self.session_plan),
            "msi_session": self.name,
        }

    def get_session_dir(self, role):
        """The directory `role` resolves to, or "." when the software emits no such data."""
        if role == INHERITED_ROLE and self.atlas_session:
            return self.atlas_session.get_session_dir(INHERITED_ROLE)
        path_type = resolve_role_path_type(self.session_plan, role)
        if not path_type:
            return "."
        return fill_place_holders(
            path_type.overlay_path,
            self.get_replacement_map(),
        )

    def get_file_pattern(self, role):
        """The filename convention expected in this session's `role` directory."""
        inherited = role == INHERITED_ROLE and self.atlas_session
        plan = self.atlas_session.group.session_plan if inherited else self.session_plan
        return resolve_role_file_pattern(plan, role)

    def _resolve_path_row(self, role):
        """The persisted `stores.Path` for `role`, created if this directory has none yet.

        Writes -- unlike `get_session_dir`, which only builds the string. Private because
        `resolve_role_paths` is the one place a session's paths are meant to be populated.
        """
        overlay_path = fill_place_holders(
            self.get_session_dir(role),
            self.get_replacement_map(),
        )
        assert_fully_resolved(overlay_path, describe="%s for session %s" % (role, self.name))
        return Path.first_or_create(overlay_path)

    @property
    def role_paths(self):
        """role -> the stores.Path stored for it, None where nothing was resolved."""
        return {role: getattr(self, role) for role in SOFTWARE_PATH_ROLES}

    def resolve_role_paths(self):
        """Fill this session's Path FKs from its plan. Does not save.

        A role with no template is left alone: absence means software doesn't produce it.
        `atlas` is inherited from the linked screening session
        """
        for role in RESOLVED_ROLES:
            if resolve_role_path_type(self.session_plan, role):
                setattr(self, role, self._resolve_path_row(role))
        if self.atlas_session:
            self.atlas = self.atlas_session.atlas

    @property
    def super_resolution(self):
        """Sessions predating acquisition settings read as not super-resolution."""
        return bool(self.acquisition and self.acquisition.super_resolution)

    def get_calibrated_pixel_size(self):
        """Return the most recent calibrated pixel spacing for this session's magnification and camera, or None."""
        if not self.magnification:
            return None
        cal = (
            CalibratedPixelSize.objects.filter(
                mag=self.magnification,
                camera=self.session_plan.camera,
            )
            .order_by("-calibrated_at")
            .first()
        )
        if cal:
            return cal.pixel_spacing
        return None

    def __str__(self):
        return "msi %s" % self.name


def parse_integer_order_list(text):
    return list((map((lambda x: int(x)), text.split(","))))


def suggest_name(prefix, model_name="MsiSession"):
    """
    Session based on prefix and then date format 24mar01.
    Make unique name by advancing to next in alphabet.
    If all are used, add one more char at the end starting from a
    """
    alphabet = string.ascii_letters
    remainders = []
    date_str = time.strftime("%y%b%d").lower()
    if prefix:
        prefix_search = prefix + date_str
    else:
        prefix_search = date_str
    model_instance = getattr(sys.modules[__name__], model_name)
    used_names = list(map((lambda x: x.name), model_instance.objects.filter(Q(name__startswith=prefix_search))))
    if not used_names:
        # first session of the day
        return prefix_search + "a"
    used_names = sorted(used_names, reverse=True)
    last_name = used_names[0]
    last_char = last_name[-1]
    if last_char == "z":
        return last_name + "a"
    else:
        try:
            my_index = alphabet.index(last_char)
            return last_name[:-1] + alphabet[my_index + 1]
        except ValueError:
            # If the last character is not in the alphabet, just append 'a'
            return last_name + "a"
        except IndexError:
            return last_name + "a"
        except Exception:
            raise


def suggest_scrn_session_name(prefix, group_instance):
    model_instance = AtlasSession
    used_names = list(
        map((lambda x: x.name), model_instance.objects.filter(Q(group=group_instance, name__startswith=prefix)))
    )
    software = group_instance.session_plan.software
    # TODO need to find a way to decide whether names are defined as Sample%d
    if software.name == "tfs multi-grid":
        return "Sample%d" % (len(used_names) + 1,)
    else:
        return suggest_name(prefix, model_name="AtlasSession")
