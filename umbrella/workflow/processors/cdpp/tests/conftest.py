"""Shared fixtures for the cdpp processor tests: plans, a cdpp run and a fake cluster."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from processes.models import Pipe, PipeInPlan, ProcPlan, ProcRun, ProcSoftware

from workflow.context import RunContext

FIXTURES = Path(__file__).parent / "fixtures"
PLAN = json.loads((FIXTURES / "plan.json").read_text())
PROGRESS = (FIXTURES / "progress.json").read_text()

ROOT = "/hpc/projects/group.czii/krios1.processing"
SESSION = "24nov10"
CDPP_DIR = f"{ROOT}/cdpp/{SESSION}/run001"


class FakeCluster:
    """Answers the processor's --plan-only SSH call."""

    def __init__(self, plan=PLAN, err=""):
        self.plan = plan
        self.err = err
        self.commands = []

    def connect(self, cluster_id=None, auth=None):
        ssh = Mock()
        ssh.exec_command.side_effect = self._exec
        return ssh

    def _exec(self, command, timeout=None):
        self.commands.append(command)
        out = ""
        if "--plan-only" in command and self.plan:
            out = f"Loading mamba\nCDPP_PLAN_BEGIN\n{json.dumps(self.plan)}\nCDPP_PLAN_END\n"
        return Mock(), _stream(out), _stream(self.err)

    @property
    def plan_commands(self):
        return [command for command in self.commands if "--plan-only" in command]


def _stream(text):
    stream = Mock()
    stream.read.return_value = text.encode()
    return stream


@pytest.fixture
def fake_cluster(monkeypatch):
    cluster = FakeCluster()
    monkeypatch.setattr("common.clusterio.get_cluster_ssh_connection", cluster.connect)
    return cluster


def _software(processor_class):
    software, _ = ProcSoftware.objects.update_or_create(
        processor_class=processor_class, defaults={"name": processor_class}
    )
    return software


@pytest.fixture
def cdpp_plans(db):
    """The plans a cdpp run touches. czii-live and czii-copick are not created by migrations."""
    _software("aretomo3")
    for plan_name, processor_class, step_name in (
        ("czii-live", "aretomo3", "vol001"),
        ("czii-copick", "copick", "copick-step"),
    ):
        plan, created = ProcPlan.objects.get_or_create(name=plan_name)
        if created:
            pipe = Pipe.objects.create(name=step_name, software=_software(processor_class))
            PipeInPlan.objects.create(name=step_name, plan=plan, step=1, pipe=pipe)
    return {plan.name: plan for plan in ProcPlan.objects.all()}


@pytest.fixture
def cdpp_step(cdpp_plans):
    return PipeInPlan.objects.select_related("plan", "pipe__software").get(plan__name="czii-cdpp")


@pytest.fixture
def cdpp_run(cdpp_step, test_msi_session):
    return ProcRun.objects.create(name="run001", proc_plan=cdpp_step.plan, msi_session=test_msi_session)


@pytest.fixture
def cdpp_context(cdpp_step, cdpp_run, test_msi_session, test_user):
    return RunContext(
        proc_run=cdpp_run,
        pipe_in_plan=cdpp_step,
        msi_session=test_msi_session,
        user=test_user,
        cluster_id="czii",
        run_number=cdpp_run.name,
        job_name=f"cdpp_{SESSION}_run001_cdpp-step",
        inputs={},
    )
