from django.db import migrations

COPICK_SCAN = {
    "task_name": "copick_scan",
    "software_name": "copick-scan",
    "processor_class": "copick-scan",
    # groups with copick in the Storage Explorer (both copick sub-processors write into 'copick')
    "storage_dirname": "copick",
    "pipe_name": "cpck_scan_j1",
    "plan_name": "copick-scan",
    "pipe_in_plan_name": "copick-scan-step",
}


def create_copick_scan_procplan(apps, schema_editor):
    Task = apps.get_model("processes", "Task")
    ProcSoftware = apps.get_model("processes", "ProcSoftware")
    Pipe = apps.get_model("processes", "Pipe")
    ProcPlan = apps.get_model("processes", "ProcPlan")
    PipeInPlan = apps.get_model("processes", "PipeInPlan")

    proc = COPICK_SCAN
    if ProcPlan.objects.filter(name=proc["plan_name"]).exists():
        print(f"  {proc['plan_name']} plan already exists, skipping")
        return

    task, _ = Task.objects.get_or_create(name=proc["task_name"], defaults={"step": 1})
    software, _ = ProcSoftware.objects.update_or_create(
        name=proc["software_name"],
        defaults={
            "processor_class": proc["processor_class"],
            "storage_dirname": proc["storage_dirname"],
            "active": True,
        },
    )
    software.capable_tasks.add(task)

    pipe = Pipe.objects.create(name=proc["pipe_name"], software=software)
    pipe.tasks_performed.add(task)

    plan = ProcPlan.objects.create(name=proc["plan_name"])
    PipeInPlan.objects.create(name=proc["pipe_in_plan_name"], plan=plan, step=1, pipe=pipe)
    print(f"  Created {proc['plan_name']} records successfully")


def reverse_copick_scan_procplan(apps, schema_editor):
    ProcPlan = apps.get_model("processes", "ProcPlan")
    Pipe = apps.get_model("processes", "Pipe")
    ProcPlan.objects.filter(name=COPICK_SCAN["plan_name"]).delete()
    Pipe.objects.filter(name=COPICK_SCAN["pipe_name"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("processes", "0049_drop_legacy_param_models"),
    ]

    operations = [
        migrations.RunPython(create_copick_scan_procplan, reverse_code=reverse_copick_scan_procplan),
    ]
