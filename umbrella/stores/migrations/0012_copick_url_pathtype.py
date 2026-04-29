from django.db import migrations, models

COPICK_TEMPLATE = {
    "data_type": "copick_url",
    "static_path": "/copick/{msi_session}/{copick_run}/",
    "overlay_path": "{http_base}{scope}.processing/copick/{msi_session}/{copick_run}/",
}


def seed_copick_pathtype(apps, schema_editor):
    StaticPath = apps.get_model("stores", "StaticPath")
    PathType = apps.get_model("stores", "PathType")
    sp, _ = StaticPath.objects.update_or_create(
        data_type=COPICK_TEMPLATE["data_type"],
        defaults={"static_path": COPICK_TEMPLATE["static_path"]},
    )
    PathType.objects.update_or_create(
        static_path=sp,
        defaults={"overlay_path": COPICK_TEMPLATE["overlay_path"]},
    )


def unseed_copick_pathtype(apps, schema_editor):
    StaticPath = apps.get_model("stores", "StaticPath")
    StaticPath.objects.filter(data_type=COPICK_TEMPLATE["data_type"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("stores", "0011_review_pathtypes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="staticpath",
            name="data_type",
            field=models.CharField(
                choices=[
                    ("atlas", "grid atlas"),
                    ("satlas", "grid atlas from screening"),
                    ("parents", "parent image of the tomography images"),
                    ("sums", "sum image of the frames"),
                    ("frames", "frames"),
                    ("rawst", "raw tilt image stack"),
                    ("tangl", "tilt angles"),
                    ("mdoc", "mdoc"),
                    ("ctf", "ctf values"),
                    ("aln", "tilt alignments"),
                    ("imod", "aln in imod compatible format for relion"),
                    ("rec", "all frame tomo recon"),
                    ("evn", "even frame tomo recon"),
                    ("odd", "odd frame tomo recon"),
                    ("deno", "denoised tomo recon"),
                    ("pick", "particle point annotation"),
                    ("seg", "segmentation"),
                    ("galr", "particle gallery"),
                    ("proc_dir", "processing directory on cluster filesystem"),
                    ("zarr_url", "zarr volume URL for tomogram viewer"),
                    ("thumb_url", "thumbnail/CTF-thumbnail URL base"),
                    ("copick_url", "copick project root URL"),
                ],
                max_length=16,
                unique=True,
            ),
        ),
        migrations.RunPython(seed_copick_pathtype, unseed_copick_pathtype),
    ]
