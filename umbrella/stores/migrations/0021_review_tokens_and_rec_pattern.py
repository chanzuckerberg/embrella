"""Retire review's legacy token dialect, and give the zarr filename convention a row.

Review templates spelled the processing software `{workflow}` and the processing run
`{run}` -- both collide with those tokens' true meanings (the imaging workflow; a per-file
tilt-series id). The same-era spellings migrate together: `{proc_software}` / `{proc_run}`.
`resolve_review_path` mirrors both spellings permanently, so an operator's un-migrated
custom row keeps resolving.
"""

from django.db import migrations

# The review lane's data types -- the only rows where {workflow}/{run} carry the legacy
# meanings. Acquisition and processing rows keep {run} as a real tilt-series id.
REVIEW_DATA_TYPES = ("proc_dir", "proc_url", "zarr_url", "thumb_url", "copick_url")

TOKEN_RENAMES = (("{workflow}", "{proc_software}"), ("{run}", "{proc_run}"))

# Keyed on (data_kind, label); code reads this row by REC_PATTERN_LABEL in
# workflow/syncers.py, so the two constants must match.
REC_PATTERN = {
    "label": "{position}_Vol.zarr",
    "list_glob": "*_Vol.zarr",
    "regex": r"^(?P<position>Position_\d+(?:_\d+)*)_Vol\.zarr$",
    "sample_filenames": ["Position_1_Vol.zarr", "Position_1_2_Vol.zarr", "Position_15_Vol.zarr"],
    "notes": "Canonical reconstruction naming; parse_zarr_filename and the copick --run-regex read this row.",
}


def _rename_tokens(apps, renames):
    PathType = apps.get_model("stores", "PathType")
    for path_type in PathType.objects.filter(data_kind__data_type__in=REVIEW_DATA_TYPES):
        overlay = path_type.overlay_path
        for old, new in renames:
            overlay = overlay.replace(old, new)
        if overlay != path_type.overlay_path:
            path_type.overlay_path = overlay
            path_type.save(update_fields=["overlay_path"])


def forward(apps, schema_editor):
    _rename_tokens(apps, TOKEN_RENAMES)

    DataKind = apps.get_model("stores", "DataKind")
    FilePattern = apps.get_model("stores", "FilePattern")
    kind, _ = DataKind.objects.get_or_create(data_type="rec")
    # update_or_create: this row is a code-shipped contract that must track the code,
    # unlike the operator-tunable acquisition patterns (get_or_create).
    FilePattern.objects.update_or_create(
        data_kind=kind,
        label=REC_PATTERN["label"],
        defaults={k: v for k, v in REC_PATTERN.items() if k != "label"},
    )


def reverse(apps, schema_editor):
    _rename_tokens(apps, [(new, old) for old, new in TOKEN_RENAMES])

    FilePattern = apps.get_model("stores", "FilePattern")
    FilePattern.objects.filter(data_kind__data_type="rec", label=REC_PATTERN["label"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("stores", "0020_split_acquisition_templates"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
