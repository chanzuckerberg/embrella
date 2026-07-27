# Generated manually for membraneseg processor

from django.db import migrations


def fix_membraneseg_processor(apps, schema_editor):
    """
    Fix membraneseg to use parameter-based input selection instead of PipeJoints.

    Changes:
    1. Update 'membraneseg' ProcSoftware to have processor_class='membraneseg'
    2. Remove PipeJoints for membraneseg (it uses parameter-based input selection)
    """
    ProcSoftware = apps.get_model("processes", "ProcSoftware")
    PipeJoint = apps.get_model("processes", "PipeJoint")
    PipeInPlan = apps.get_model("processes", "PipeInPlan")

    # 1. Update 'membraneseg' ProcSoftware to have processor_class='membraneseg'
    try:
        membr_sw = ProcSoftware.objects.get(name="membraneseg")
        membr_sw.processor_class = "membraneseg"
        membr_sw.default_cluster = "bruno"
        membr_sw.allowed_clusters = ["bruno", "czii"]
        membr_sw.active = True
        membr_sw.save()
        print(f"✓ Updated membraneseg ProcSoftware: processor_class='membraneseg'")
    except ProcSoftware.DoesNotExist:
        print("⚠ 'membraneseg' ProcSoftware not found - skipping update")

    # 2. Remove PipeJoints for membraneseg (uses parameter-based input selection)
    try:
        membr_pip = PipeInPlan.objects.filter(plan__name="membraneseg", pipe__software__name="membraneseg").first()

        if membr_pip:
            membr_joints = PipeJoint.objects.filter(pipe_in_plan=membr_pip)
            count = membr_joints.count()
            if count > 0:
                membr_joints.delete()
                print(f"✓ Deleted {count} PipeJoint(s) for membraneseg")
            else:
                print("✓ No PipeJoints for membraneseg")
    except Exception as e:
        print(f"⚠ Could not remove membraneseg PipeJoints: {e}")


def reverse_fix(apps, schema_editor):
    """
    Reverse the migration (note: this won't perfectly restore the old state).
    """
    ProcSoftware = apps.get_model("processes", "ProcSoftware")

    try:
        membr_sw = ProcSoftware.objects.get(name="membraneseg")
        membr_sw.processor_class = None
        membr_sw.default_cluster = None
        membr_sw.allowed_clusters = None
        membr_sw.save()
        print("✓ Reversed membraneseg ProcSoftware changes")
    except ProcSoftware.DoesNotExist:
        print("⚠ 'membraneseg' ProcSoftware not found - skipping reverse")

    print("⚠ Note: PipeJoints were not recreated. If needed, restore from backup.")


class Migration(migrations.Migration):
    dependencies = [
        ("processes", "0035_init_copick_action_procplans"),
    ]

    operations = [
        migrations.RunPython(
            fix_membraneseg_processor,
            reverse_code=reverse_fix,
        ),
    ]
