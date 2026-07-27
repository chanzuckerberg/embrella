# Generated manually for copick action processors

from django.db import migrations


# Processor metadata (matching workflow/processors/copick/*)
COPICK_ACTION_PROCESSORS = [
    {
        "task_name": "copick_add_object",
        "software_name": "copick-add-object",
        "version": "1.0",
        "processor_class": "copick-add-object",
        "default_cluster": "bruno",
        "allowed_clusters": ["bruno"],
        "script_directory": "/hpc/projects/group.czii/krios1.processing/copick/scripts",
        "pipe_name": "cpck_add_obj_j1",
        "plan_name": "copick-add-object",
        "pipe_in_plan_name": "copick-add-object-step",
    },
    {
        "task_name": "copick_import",
        "software_name": "copick-import",
        "version": "1.0",
        "processor_class": "copick-import",
        "default_cluster": "bruno",
        "allowed_clusters": ["bruno"],
        "script_directory": "/hpc/projects/group.czii/krios1.processing/copick/scripts",
        "pipe_name": "cpck_import_j1",
        "plan_name": "copick-import",
        "pipe_in_plan_name": "copick-import-step",
    },
]


def create_copick_action_procplans(apps, schema_editor):
    """
    Create Task, ProcSoftware, Pipe, ProcPlan, and PipeInPlan records for copick action processors.

    - copick-add-object: For adding pickable objects to existing Copick projects
    - copick-import: For importing additional tomograms to existing projects
    """
    Task = apps.get_model("processes", "Task")
    ProcSoftware = apps.get_model("processes", "ProcSoftware")
    Pipe = apps.get_model("processes", "Pipe")
    ProcPlan = apps.get_model("processes", "ProcPlan")
    PipeInPlan = apps.get_model("processes", "PipeInPlan")

    for proc in COPICK_ACTION_PROCESSORS:
        plan_name = proc["plan_name"]

        if ProcPlan.objects.filter(name=plan_name).exists():
            print(f"  {plan_name} plan already exists, skipping")
            continue

        # Create or get Task
        task, task_created = Task.objects.get_or_create(name=proc["task_name"], defaults={"step": 1})
        if task_created:
            print(f"  Created Task: {task.name}")

        # Create or update ProcSoftware
        software, sw_created = ProcSoftware.objects.update_or_create(
            name=proc["software_name"],
            defaults={
                "version": proc["version"],
                "processor_class": proc["processor_class"],
                "default_cluster": proc["default_cluster"],
                "allowed_clusters": proc["allowed_clusters"],
                "script_directory": proc["script_directory"],
                "active": True,
            },
        )
        if sw_created:
            print(f"  Created ProcSoftware: {software.name}")

        # Associate Task with ProcSoftware
        software.capable_tasks.add(task)

        # Create Pipe
        pipe = Pipe.objects.create(
            name=proc["pipe_name"],
            software=software,
        )
        pipe.tasks_performed.add(task)
        print(f"  Created Pipe: {pipe.name}")

        # Create ProcPlan
        plan = ProcPlan.objects.create(name=plan_name)
        print(f"  Created ProcPlan: {plan.name}")

        # Create PipeInPlan
        PipeInPlan.objects.create(
            name=proc["pipe_in_plan_name"],
            plan=plan,
            step=1,
            pipe=pipe,
        )
        print(f"  Created {plan_name} records successfully")


def reverse_copick_action_procplans(apps, schema_editor):
    """Remove the copick action processor records."""
    ProcPlan = apps.get_model("processes", "ProcPlan")
    Pipe = apps.get_model("processes", "Pipe")

    # Delete ProcPlans (cascades to PipeInPlan)
    ProcPlan.objects.filter(name__in=["copick-add-object", "copick-import"]).delete()

    # Delete Pipes
    Pipe.objects.filter(name__in=["cpck_add_obj_j1", "cpck_import_j1"]).delete()

    print("  Removed copick action processor records")


class Migration(migrations.Migration):
    dependencies = [
        ("processes", "0034_add_filesystem_survey_models"),
    ]

    operations = [
        migrations.RunPython(
            create_copick_action_procplans,
            reverse_code=reverse_copick_action_procplans,
        ),
    ]
