"""Backfill ReviewTomogram.file_path for rows synced before the column existed.

The syncer now stores the run-relative path it discovers on disk; older rows were all
discovered under the naming this renders, so rendering it once is exact:
DCTF -> vol001/<position>_Vol.zarr, SART -> vol003/<position>_Vol.zarr,
Denoised -> <position>_Vol.zarr (denoise writes directly under the run directory).
"""

from django.db import migrations
from django.db.models import F, Value
from django.db.models.functions import Concat

# reconstruction_type -> vol subdir, matching AretomoSyncer/DenoiseSyncer layout.
RECON_TYPE_TO_VOL_DIR = {
    "DCTF": "vol001",
    "SART": "vol003",
    "Denoised": "",
}

REC_SUFFIX = "_Vol.zarr"


def forward(apps, schema_editor):
    ReviewTomogram = apps.get_model("processes", "ReviewTomogram")
    for recon_type, vol_dir in RECON_TYPE_TO_VOL_DIR.items():
        prefix = f"{vol_dir}/" if vol_dir else ""
        ReviewTomogram.objects.filter(reconstruction_type=recon_type).update(
            file_path=Concat(Value(prefix), F("position_id"), Value(REC_SUFFIX))
        )


def reverse(apps, schema_editor):
    ReviewTomogram = apps.get_model("processes", "ReviewTomogram")
    ReviewTomogram.objects.filter(reconstruction_type__in=RECON_TYPE_TO_VOL_DIR).update(file_path="")


class Migration(migrations.Migration):
    dependencies = [
        ("processes", "0046_reviewtomogram_file_path"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
