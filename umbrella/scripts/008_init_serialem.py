"""Register the serialEM acquisition software on krios1 and krios2.

One Software row serves both scopes, so per-plan path bindings are used for krios2's overrides.

- The software default will be krios1's
- krios2 (K3) writes a differently-shaped tree, so its plan binds its own directories.
- Each plan binds its own rec naming (tilt_series role) -- the stems differ per scope.

Idempotent: every row is get_or_create, so re-running repairs a partial state, never
duplicates, and never clobbers admin edits. Run inside the devcontainer:

    python umbrella/manage.py runscript 008_init_serialem
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "umbrella.settings")
django.setup()

from stores.models import DataKind, FilePattern, PathType
from tem.models import (
    TILT_SERIES_ROLE,
    Camera,
    ImagingWorkflow,
    Microscope,
    SessionPlan,
    SessionPlanPathBinding,
    Software,
)

DEFAULT_SESSION_DIR = "/hpc/instruments/czii.{scope}/OffloadData/TemScripting/EF-Falcon/serialem/{msi_session}/"
DEFAULT_FRAMES = {"label": "serialEM frames (eer)", "list_glob": "*.eer", "regex": r"^(?P<run>.+)\.eer$"}
CELTIC_FRAMES = {"label": "serialEM frames (tif)", "list_glob": "*.tif", "regex": r"^(?P<run>.+)\.tif$"}

# Everything scope-specific in one place. `name_prefix` is the letter the New Session form
# puts in front of suggested names (s26jun08a / p26jun08a) so the two serialEM plans are
# told apart. `session_dir` differing from the default gets
# bound on that scope's plan. `rec` names the reconstruction zarrs: the stem is the
# tilt-series stack name (capture excludes .mrc, so position_id reads "pt712_ts_001"),
# the _Vol.zarr tail is a static match. Copick derives --run-regex by replacing a
# literal \.zarr$ tail -- keep that spelling.
SCOPES = {
    "krios1": {
        "name_prefix": "s",
        "camera": {
            "name": "Falcon4i",
            "root_dir": "/hpc/instruments/czii.krios1/OffloadData/",
            "frame_format": "eer",
            "initial_frame_base_dir": "/OffloadData/",
        },
        "session_dir": DEFAULT_SESSION_DIR,
        "frames": DEFAULT_FRAMES,
        "rec": {
            "label": "serialEM rec (krios1)",
            "regex": r"^(?P<position>Position_\d+(?:_\d+)*_ts_\d+)\.mrc_Vol\.zarr$",
            "samples": ["Position_10_ts_001.mrc_Vol.zarr"],
        },
    },
    "krios2": {
        "name_prefix": "p",
        "camera": {
            "name": "GatanCeltic",
            "root_dir": "/hpc/instruments/czii.krios2.k3/k3f/",
            "frame_format": "tif",
            "initial_frame_base_dir": "/k3f_serialem/",
        },
        "session_dir": "/hpc/instruments/czii.krios2.k3/k3f/k3f_serialem/{msi_session}/",
        "frames": CELTIC_FRAMES,
        "rec": {
            "label": "serialEM rec (krios2)",
            "regex": r"^(?P<position>pt\d+_ts_\d+)\.mrc_Vol\.zarr$",
            "samples": ["pt712_ts_001.mrc_Vol.zarr", "pt729_ts_001.mrc_Vol.zarr", "pt729_ts_002.mrc_Vol.zarr"],
        },
    },
}


def get_camera(spec):
    """The camera row by name; field defaults apply only on first creation."""
    camera, _ = Camera.objects.get_or_create(
        name=spec["name"], defaults={field: value for field, value in spec.items() if field != "name"}
    )
    return camera


def get_pattern(data_type, label, *, list_glob, regex, samples=(), notes=""):
    """The (kind, label) row, validated against its samples."""
    kind, _ = DataKind.objects.get_or_create(data_type=data_type)
    pattern, _ = FilePattern.objects.get_or_create(
        data_kind=kind,
        label=label,
        defaults={"list_glob": list_glob, "regex": regex, "sample_filenames": list(samples), "notes": notes},
    )
    pattern.full_clean()
    return pattern


def get_path_type(data_type, directory, file_pattern):
    kind, _ = DataKind.objects.get_or_create(data_type=data_type)
    path_type, _ = PathType.objects.get_or_create(
        data_kind=kind,
        overlay_path=directory,
        cluster=None,
        defaults={"file_pattern": file_pattern},
    )
    return path_type


def mdoc_pattern():
    return get_pattern(
        "mdoc",
        "serialEM {run}.mrc.mdoc",
        list_glob="*.mrc.mdoc",
        regex=r"^(?P<run>\w+_ts_\d+)\.mrc\.mdoc$",
        samples=["Position_10_ts_001.mrc.mdoc", "pt712_ts_001.mrc.mdoc"],
    )


def frames_pattern(spec):
    return get_pattern(
        "frames",
        spec["label"],
        list_glob=spec["list_glob"],
        regex=spec["regex"],
        notes="Frame naming unverified -- tighten the regex from a real listing.",
    )


def serialem_software():
    """Steps 3-4: the software row and its default directory templates."""
    software, _ = Software.objects.get_or_create(
        name="serialEM",
        version="",
        defaults={
            "mdocs": get_path_type("mdoc", DEFAULT_SESSION_DIR, mdoc_pattern()),
            "frames": get_path_type("frames", DEFAULT_SESSION_DIR, frames_pattern(DEFAULT_FRAMES)),
        },
    )
    return software


def bind_session_dirs(plan, spec):
    """Step 8: this scope's tree deviates from the default -- bind its own directories.
    The frames pattern rides the directory row, so the scope's frame format comes along."""
    for role, data_type, pattern in (
        ("mdocs", "mdoc", mdoc_pattern()),
        ("frames", "frames", frames_pattern(spec["frames"])),
    ):
        SessionPlanPathBinding.objects.get_or_create(
            session_plan=plan,
            role=role,
            defaults={"path_type": get_path_type(data_type, spec["session_dir"], pattern)},
        )


def plans_and_bindings(software):
    """Steps 6+8: one plan per scope; bindings only where the scope deviates."""
    workflow, _ = ImagingWorkflow.objects.get_or_create(imaging_mode="tem", workflow="tomo")

    for scope_name, spec in SCOPES.items():
        plan, _ = SessionPlan.objects.get_or_create(
            scope=Microscope.objects.get(name=scope_name),
            camera=get_camera(spec["camera"]),
            imaging_workflow=workflow,
            software=software,
            defaults={"name_prefix": spec["name_prefix"]},
        )
        # Plans created before the field existed have a blank prefix: fill it, but leave any value
        # an admin already chose.
        if not plan.name_prefix:
            plan.name_prefix = spec["name_prefix"]
            plan.save(update_fields=["name_prefix"])

        if spec["session_dir"] != DEFAULT_SESSION_DIR:
            bind_session_dirs(plan, spec)

        rec = spec["rec"]
        pattern = get_pattern("rec", rec["label"], list_glob="*_Vol.zarr", regex=rec["regex"], samples=rec["samples"])
        SessionPlanPathBinding.objects.get_or_create(
            session_plan=plan, role=TILT_SERIES_ROLE, defaults={"file_pattern": pattern}
        )
        print(
            f"plan {plan.id}: {scope_name} serialEM ({spec['camera']['name']}), "
            f"prefix '{plan.name_prefix}', {TILT_SERIES_ROLE} -> {rec['label']}"
        )


def run():
    software = serialem_software()
    plans_and_bindings(software)

    print(
        "\nReminder: the serialEM frames regex is a loose placeholder -- tighten it from a "
        "real listing (noted on the FilePattern row)."
    )


if __name__ == "__main__":
    run()
