"""{proc_software} resolves to the directory a software owns"""

import pytest
from tem.models import MsiSession

from processes.models import Pipe, PipeInPlan, ProcPlan, ProcRun, ProcSoftware


@pytest.fixture
def msi_session(db, session_plan):
    return MsiSession.objects.create(name="24nov10", session_plan=session_plan)


def _pipe_in_plan(software):
    plan = ProcPlan.objects.create(name="test-plan")
    pipe = Pipe.objects.create(name="vol001", software=software)
    return PipeInPlan.objects.create(name="vol001", plan=plan, pipe=pipe)


@pytest.mark.django_db
class TestProcSoftwareDirname:
    def test_falls_back_to_name_when_blank(self):
        s = ProcSoftware.objects.create(name="fixture-solo", processor_class="fixture-solo")
        assert s.storage_dirname == ""
        assert s.dirname == "fixture-solo"

    def test_prefers_storage_dirname(self):
        """The shape of the copick case: distinct softwares sharing one directory."""
        s = ProcSoftware.objects.create(
            name="fixture-import", processor_class="fixture-import", storage_dirname="fixture"
        )
        assert s.dirname == "fixture"


@pytest.mark.django_db
class TestProcSoftwareTokenSubstitution:
    def test_proc_software_token_is_the_directory(self, msi_session):
        """Substituting `name` would resolve to /fixture-import/, a directory that does not
        exist -- the files are under /fixture/. Real instance of this: the copick
        sub-processors, which all write into `copick`.

        Fixture names avoid the real ones on purpose: `workflow.apps` syncs the processor
        registry into the database at startup, and main made `processor_class` unique, so
        creating a `copick-import` row here collides.
        """
        software = ProcSoftware.objects.create(
            name="fixture-import", processor_class="fixture-import", storage_dirname="fixture"
        )
        pip = _pipe_in_plan(software)
        run = ProcRun.objects.create(name="run001", proc_plan=pip.plan, msi_session=msi_session)

        mapping = pip.get_replacement_map(proc_run=run, msi_session=msi_session)

        assert mapping["proc_software"] == "fixture"
        # {workflow} is the legacy alias of {proc_software}; it has to track it.
        assert mapping["workflow"] == "fixture"

    def test_run_context_agrees_with_pipe_in_plan(self, msi_session):
        """Two maps, one contract -- they must not drift apart."""
        from django.contrib.auth.models import User
        from workflow.execution import RunContext

        software = ProcSoftware.objects.create(
            name="fixture-import", processor_class="fixture-import", storage_dirname="fixture"
        )
        pip = _pipe_in_plan(software)
        run = ProcRun.objects.create(name="run001", proc_plan=pip.plan, msi_session=msi_session)
        context = RunContext(
            proc_run=run,
            pipe_in_plan=pip,
            msi_session=msi_session,
            user=User.objects.create_user(username="t", password="p"),
            cluster_id="czii",
            run_number="run001",
            job_name="job",
            inputs={},
        )

        assert context.get_placeholder_map()["proc_software"] == "fixture"
        assert (
            context.get_placeholder_map()["proc_software"]
            == pip.get_replacement_map(proc_run=run, msi_session=msi_session)["proc_software"]
        )
