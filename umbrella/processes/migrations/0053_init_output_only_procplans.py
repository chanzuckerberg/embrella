from django.db import migrations

# Processor metadata (matching workflow/processors/output_only/processor.py). These tools
# run in an external pipeline; the plans exist so their runs can be recorded as ProcRuns.
OUTPUT_ONLY_PROCESSORS = [
    {
        "task_name": "alignment_refinement",
        "processor_class": "miss_alignment",
        "pipe_name": "miss_alignment_j1",
        "plan_name": "czii-miss-alignment",
        "plan_display_name": "Miss-alignment refinement",
        "pipe_in_plan_name": "miss-alignment-step",
    },
    {
        "task_name": "missing_wedge_correction",
        "processor_class": "isonet2",
        "pipe_name": "isonet2_j1",
        "plan_name": "czii-isonet2",
        "plan_display_name": "IsoNet2",
        "pipe_in_plan_name": "isonet2-step",
    },
    {
        "task_name": "missing_wedge_correction",
        "processor_class": "deepdewedge",
        "pipe_name": "deepdewedge_j1",
        "plan_name": "czii-deepdewedge",
        "plan_display_name": "DeepDeWedge",
        "pipe_in_plan_name": "deepdewedge-step",
    },
    {
        "task_name": "missing_wedge_correction",
        "processor_class": "icecream",
        "pipe_name": "icecream_j1",
        "plan_name": "czii-icecream",
        "plan_display_name": "ICECREAM",
        "pipe_in_plan_name": "icecream-step",
    },
]


def create_output_only_procplans(apps, schema_editor):
    Task = apps.get_model("processes", "Task")
    ProcSoftware = apps.get_model("processes", "ProcSoftware")
    Pipe = apps.get_model("processes", "Pipe")
    ProcPlan = apps.get_model("processes", "ProcPlan")
    PipeInPlan = apps.get_model("processes", "PipeInPlan")

    for proc in OUTPUT_ONLY_PROCESSORS:
        if ProcPlan.objects.filter(name=proc["plan_name"]).exists():
            print(f"  {proc['plan_name']} plan already exists, skipping")
            continue

        task, _ = Task.objects.get_or_create(name=proc["task_name"], defaults={"step": 1})
        # Keyed on processor_class (unique): the startup sync may already have created the row.
        software, _ = ProcSoftware.objects.get_or_create(
            processor_class=proc["processor_class"],
            defaults={"name": proc["processor_class"], "version": "external", "active": True},
        )
        software.capable_tasks.add(task)

        pipe = Pipe.objects.create(name=proc["pipe_name"], software=software)
        pipe.tasks_performed.add(task)

        plan = ProcPlan.objects.create(name=proc["plan_name"], display_name=proc["plan_display_name"])
        PipeInPlan.objects.create(name=proc["pipe_in_plan_name"], plan=plan, step=1, pipe=pipe)
        print(f"  Created {proc['plan_name']} records successfully")


def reverse_output_only_procplans(apps, schema_editor):
    ProcPlan = apps.get_model("processes", "ProcPlan")
    Pipe = apps.get_model("processes", "Pipe")
    ProcPlan.objects.filter(name__in=[proc["plan_name"] for proc in OUTPUT_ONLY_PROCESSORS]).delete()
    Pipe.objects.filter(name__in=[proc["pipe_name"] for proc in OUTPUT_ONLY_PROCESSORS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("processes", "0052_procsoftware_cluster_from_db"),
    ]

    operations = [
        migrations.RunPython(create_output_only_procplans, reverse_code=reverse_output_only_procplans),
    ]
