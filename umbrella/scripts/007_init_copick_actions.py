"""
Initialize database records for Copick action processors.

This script creates Pipe, ProcPlan, and PipeInPlan records for copick-related
action processors. Task and ProcSoftware records are expected to already exist.

- copick-add-object: For adding pickable objects to existing Copick projects

Future additions may include:
- copick-import-tomograms: For importing additional tomograms to existing projects

Run this script:
    just manage runscript 007_init_copick_actions
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "umbrella.settings")
django.setup()

from processes.models import (
    Pipe,
    PipeInPlan,
    ProcPlan,
    ProcSoftware,
    Task,
)


def create_copick_add_object():
    """Create database records for copick-add-object processor."""
    print("Creating copick-add-object processor records...")

    # Check if already exists
    if ProcPlan.objects.filter(name='copick-add-object').exists():
        print("  copick-add-object plan already exists, skipping...")
        return

    # Get existing Task and ProcSoftware
    task = Task.objects.get(name='copick_add_object')
    print(f"  Found existing Task: {task}")

    software = ProcSoftware.objects.get(name='copick-add-object')
    print(f"  Found existing ProcSoftware: {software}")

    # Create Pipe
    pipe = Pipe.objects.create(
        name='cpck_add_obj_j1',
        software=software,
    )
    pipe.tasks_performed.add(task)
    print(f"  Created Pipe: {pipe}")

    # Create ProcPlan
    plan = ProcPlan.objects.create(name='copick-add-object')
    print(f"  Created ProcPlan: {plan}")

    # Create PipeInPlan
    pipe_in_plan = PipeInPlan.objects.create(
        name='copick-add-object-step',
        plan=plan,
        step=1,
        pipe=pipe,
    )
    print(f"  Created PipeInPlan: {pipe_in_plan}")

    print("  copick-add-object processor records created successfully!")


def run():
    """Main entry point."""
    print("=" * 60)
    print("Initializing Copick Action Processors")
    print("=" * 60)

    create_copick_add_object()

    # Future: Add import_tomograms processor here
    # create_copick_import_tomograms()

    print("=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    run()
