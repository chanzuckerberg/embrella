# Generated manually for copick action processors

from django.db import migrations


def create_copick_action_procplans(apps, schema_editor):
    """
    Create Pipe, ProcPlan, and PipeInPlan records for copick action processors.

    - copick-add-object: For adding pickable objects to existing Copick projects
    - copick-import: For importing additional tomograms to existing projects

    Task and ProcSoftware records are created by workflow app sync on startup.
    """
    Task = apps.get_model('processes', 'Task')
    ProcSoftware = apps.get_model('processes', 'ProcSoftware')
    Pipe = apps.get_model('processes', 'Pipe')
    ProcPlan = apps.get_model('processes', 'ProcPlan')
    PipeInPlan = apps.get_model('processes', 'PipeInPlan')

    # Create copick-add-object records
    if not ProcPlan.objects.filter(name='copick-add-object').exists():
        try:
            task = Task.objects.get(name='copick_add_object')
            software = ProcSoftware.objects.get(name='copick-add-object')

            pipe = Pipe.objects.create(
                name='cpck_add_obj_j1',
                software=software,
            )
            pipe.tasks_performed.add(task)
            print(f"  Created Pipe: {pipe}")

            plan = ProcPlan.objects.create(name='copick-add-object')
            print(f"  Created ProcPlan: {plan}")

            PipeInPlan.objects.create(
                name='copick-add-object-step',
                plan=plan,
                step=1,
                pipe=pipe,
            )
            print("  Created copick-add-object records")
        except (Task.DoesNotExist, ProcSoftware.DoesNotExist) as e:
            print(f"  Skipping copick-add-object: {e}")
    else:
        print("  copick-add-object plan already exists, skipping")

    # Create copick-import records
    if not ProcPlan.objects.filter(name='copick-import').exists():
        try:
            task = Task.objects.get(name='copick_import')
            software = ProcSoftware.objects.get(name='copick-import')

            pipe = Pipe.objects.create(
                name='cpck_import_j1',
                software=software,
            )
            pipe.tasks_performed.add(task)
            print(f"  Created Pipe: {pipe}")

            plan = ProcPlan.objects.create(name='copick-import')
            print(f"  Created ProcPlan: {plan}")

            PipeInPlan.objects.create(
                name='copick-import-step',
                plan=plan,
                step=1,
                pipe=pipe,
            )
            print("  Created copick-import records")
        except (Task.DoesNotExist, ProcSoftware.DoesNotExist) as e:
            print(f"  Skipping copick-import: {e}")
    else:
        print("  copick-import plan already exists, skipping")


def reverse_copick_action_procplans(apps, schema_editor):
    """Remove the copick action processor records."""
    ProcPlan = apps.get_model('processes', 'ProcPlan')
    Pipe = apps.get_model('processes', 'Pipe')

    # Delete ProcPlans (cascades to PipeInPlan)
    ProcPlan.objects.filter(name__in=['copick-add-object', 'copick-import']).delete()

    # Delete Pipes
    Pipe.objects.filter(name__in=['cpck_add_obj_j1', 'cpck_import_j1']).delete()

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
