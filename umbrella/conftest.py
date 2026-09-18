"""
Pytest configuration for Django tests.

This file ensures Django is configured before any test modules are imported,
which is necessary because test files import Django models at the module level.
"""

import os

# Force SQLite for tests (override USE_MYSQL if set). PYTEST_MYSQL=True keeps
# the MariaDB config so the PyMySQL driver path can be exercised on demand.
if os.getenv("PYTEST_MYSQL") != "True":
    os.environ["USE_MYSQL"] = "False"

# Set the settings module before importing anything else
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "umbrella.settings")

import django

# Ensure Django is set up before test collection
django.setup()

import pytest
from django.contrib.auth.models import User
from processes.models import Pipe, PipeInPlan, ProcPlan, ProcRun, ProcSoftware, Task
from tem.models import Camera, ImagingWorkflow, Microscope, MsiSession, SessionPlan, Software

# Shared building blocks for the session -> plan -> processing-run chain most workflow
# tests need. A test file needing a different shape shadows these with its own fixture.


@pytest.fixture
def test_user(db):
    return User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")


@pytest.fixture
def test_session_plan(db):
    """The minimal acquisition plan: scope, camera, imaging workflow, software."""
    return SessionPlan.objects.create(
        scope=Microscope.objects.create(name="TestScope", cs=2.7),
        camera=Camera.objects.create(
            name="TestCamera",
            root_dir="/test/root",
            frame_format="eer",
            initial_frame_base_dir="/test/frames",
        ),
        imaging_workflow=ImagingWorkflow.objects.create(imaging_mode="tem", workflow="tomo"),
        software=Software.objects.create(name="TestSoftware"),
    )


@pytest.fixture
def test_msi_session(db, test_session_plan):
    return MsiSession.objects.create(name="24nov10", session_plan=test_session_plan)


@pytest.fixture
def test_proc_software(db):
    software = ProcSoftware.objects.create(
        name="test_software",
        version="1.0.0",
        processor_class="test_processor",
        default_cluster="czii",
    )
    software.capable_tasks.add(Task.objects.create(name="test_task"))
    return software


@pytest.fixture
def test_pipe(db, test_proc_software):
    return Pipe.objects.create(name="test_pipe", software=test_proc_software)


@pytest.fixture
def test_proc_plan(db):
    return ProcPlan.objects.create(name="test_plan")


@pytest.fixture
def test_pipe_in_plan(db, test_proc_plan, test_pipe):
    return PipeInPlan.objects.create(plan=test_proc_plan, pipe=test_pipe, step=1, name="test_step")


@pytest.fixture
def test_proc_run(db, test_proc_plan, test_msi_session):
    return ProcRun.objects.create(name="run001", proc_plan=test_proc_plan, msi_session=test_msi_session)
