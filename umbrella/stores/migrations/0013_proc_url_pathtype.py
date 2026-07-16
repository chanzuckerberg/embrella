from django.db import migrations, models

PROC_URL_TEMPLATE = {
    "data_type": "proc_url",
    "static_path": "/{workflow}/{msi_session}/{run}/proc_url",
    "overlay_path": "{http_base}{scope}.processing/{workflow}/{msi_session}/{run}/",
}


def seed_proc_url_pathtype(apps, schema_editor):
    StaticPath = apps.get_model("stores", "StaticPath")
    PathType = apps.get_model("stores", "PathType")
    sp, _ = StaticPath.objects.update_or_create(
        data_type=PROC_URL_TEMPLATE["data_type"],
        defaults={"static_path": PROC_URL_TEMPLATE["static_path"]},
    )
    PathType.objects.update_or_create(
        static_path=sp,
        defaults={"overlay_path": PROC_URL_TEMPLATE["overlay_path"]},
    )


def unseed_proc_url_pathtype(apps, schema_editor):
    StaticPath = apps.get_model("stores", "StaticPath")
    StaticPath.objects.filter(data_type=PROC_URL_TEMPLATE["data_type"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("stores", "0012_copick_url_pathtype"),
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
                    ("proc_url", "processing directory URL"),
                    ("zarr_url", "zarr volume URL for tomogram viewer"),
                    ("thumb_url", "thumbnail/CTF-thumbnail URL base"),
                    ("copick_url", "copick project root URL"),
                ],
                max_length=16,
                unique=True,
            ),
        ),
        migrations.RunPython(seed_proc_url_pathtype, unseed_proc_url_pathtype),
    ]
