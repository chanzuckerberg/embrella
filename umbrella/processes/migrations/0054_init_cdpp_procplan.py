from django.db import migrations

# Processor metadata (matching workflow/processors/cdpp/processor.py). The cdpp run holds
# the pipeline's config, Nextflow state and driver log; its tool outputs are recorded as
# runs of the output-only plans.
CDPP = {
    "task_name": "cryoet_pipeline",
    "software_name": "cdpp",
    "version": "0.1.0",
    "processor_class": "cdpp",
    "storage_dirname": "cdpp",
    "pipe_name": "cdpp_j1",
    "plan_name": "czii-cdpp",
    "plan_display_name": "CryoET Data Portal Pipeline",
    "pipe_in_plan_name": "cdpp-step",
}


def create_cdpp_procplan(apps, schema_editor):
    Task = apps.get_model("processes", "Task")
    ProcSoftware = apps.get_model("processes", "ProcSoftware")
    Pipe = apps.get_model("processes", "Pipe")
    ProcPlan = apps.get_model("processes", "ProcPlan")
    PipeInPlan = apps.get_model("processes", "PipeInPlan")

    proc = CDPP
    if ProcPlan.objects.filter(name=proc["plan_name"]).exists():
        print(f"  {proc['plan_name']} plan already exists, skipping")
        return

    task, _ = Task.objects.get_or_create(name=proc["task_name"], defaults={"step": 1})
    # Keyed on processor_class (unique): the startup sync may already have created the row.
    software, _ = ProcSoftware.objects.get_or_create(
        processor_class=proc["processor_class"],
        defaults={"name": proc["software_name"], "version": proc["version"], "active": True},
    )
    software.storage_dirname = proc["storage_dirname"]
    software.save(update_fields=["storage_dirname"])
    software.capable_tasks.add(task)

    pipe = Pipe.objects.create(name=proc["pipe_name"], software=software)
    pipe.tasks_performed.add(task)

    plan = ProcPlan.objects.create(name=proc["plan_name"], display_name=proc["plan_display_name"])
    PipeInPlan.objects.create(name=proc["pipe_in_plan_name"], plan=plan, step=1, pipe=pipe)
    print(f"  Created {proc['plan_name']} records successfully")


def reverse_cdpp_procplan(apps, schema_editor):
    ProcPlan = apps.get_model("processes", "ProcPlan")
    Pipe = apps.get_model("processes", "Pipe")
    ProcPlan.objects.filter(name=CDPP["plan_name"]).delete()
    Pipe.objects.filter(name=CDPP["pipe_name"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("processes", "0053_init_output_only_procplans"),
    ]

    operations = [
        migrations.RunPython(create_cdpp_procplan, reverse_code=reverse_cdpp_procplan),
    ]
