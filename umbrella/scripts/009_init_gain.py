"""Register the `gain` data kind and where each camera keeps its gain reference.

Gain depends on the camera, not the acquisition software, so the template hangs off
`Camera.gain` (as frames hang off `Software.frames`); a plan binding can still override.

    Falcon4i      shared folder, several .gain files, newest by {timestamp}
    GatanCeltic   one .dm4 beside the frames, in the session folder

Cameras not listed here (GatanK3, Ceta) stay unset: the launch form then offers no listed
gain files and the user gives an absolute path.

Idempotent: every row is get_or_create and a camera's gain is only set when blank, so
re-running repairs a partial state, never duplicates, and never clobbers admin edits.
Run inside the devcontainer, after `migrate`:

    python umbrella/manage.py runscript 009_init_gain
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "umbrella.settings")
django.setup()

from stores.models import DataKind, FilePattern, PathType
from tem.models import Camera

GAIN_KIND = "gain"

# camera name -> its gain directory template and filename convention
CAMERAS = {
    "Falcon4i": {
        "directory": "/hpc/instruments/czii.krios1/OffloadData/ImagesForProcessing/EF-Falcon/300kV/",
        "label": "Falcon4i EER gain ({timestamp})",
        "list_glob": "*.gain",
        "regex": r"^(?P<timestamp>\d{8}_\d{6})_.+\.gain$",
        "samples": ["20251218_093959_EER_GainReference.gain"],
    },
    "GatanCeltic": {
        # Same directory the krios2 serialEM plan binds for frames and mdocs; a separate
        # PathType row since rows are per kind.
        "directory": "/hpc/instruments/czii.krios2.k3/k3f/k3f_serialem/{msi_session}/",
        "label": "GatanCeltic serialEM gain (dm4)",
        "list_glob": "*.dm4",
        "regex": r"^(?P<stem>.+)\.dm4$",
        "samples": [],
        "notes": "One per session folder, so the newest by mtime is the one.",
    },
}


def get_pattern(spec):
    """The (kind, label) row, validated against its samples."""
    kind, _ = DataKind.objects.get_or_create(data_type=GAIN_KIND)
    pattern, _ = FilePattern.objects.get_or_create(
        data_kind=kind,
        label=spec["label"],
        defaults={
            "list_glob": spec["list_glob"],
            "regex": spec["regex"],
            "sample_filenames": spec["samples"],
            "notes": spec.get("notes", ""),
        },
    )
    pattern.full_clean()
    return pattern


def get_path_type(spec):
    kind, _ = DataKind.objects.get_or_create(data_type=GAIN_KIND)
    path_type, _ = PathType.objects.get_or_create(
        data_kind=kind,
        overlay_path=spec["directory"],
        cluster=None,
        defaults={"file_pattern": get_pattern(spec)},
    )
    return path_type


def set_camera_gain(name, spec):
    """Point the camera at its gain template, unless an admin already chose one."""
    camera = Camera.objects.filter(name=name).first()
    if camera is None:
        print(f"camera {name} not found -- run the acquisition init scripts first; skipped")
        return
    if camera.gain_id:
        print(f"camera {name}: gain already set -> {camera.gain.overlay_path}")
        return

    camera.gain = get_path_type(spec)
    camera.save(update_fields=["gain"])
    print(f"camera {name}: gain -> {camera.gain.overlay_path} ({camera.gain.file_pattern.list_glob})")


def run():
    for name, spec in CAMERAS.items():
        set_camera_gain(name, spec)


if __name__ == "__main__":
    run()
