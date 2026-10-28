"""
CryoET Data Portal Pipeline (cdpp) processor.

Runs the cdpp pipeline on an AreTomo3 run of the session. The SLURM job is the pipeline's
Nextflow driver (``submit-nextflow --foreground``); the pipeline submits its own step jobs.

Outputs go into Embrella's per-tool trees, ``{processing_root}/<tool>/{session}/{runNNN}/``,
one ProcRun per tree. Before submission, ``reserve_runs`` asks the pipeline for the tree
fingerprints (``config from-aretomo3 --plan-only``, read-only over SSH): a tree whose
fingerprint matches an earlier run's reuses that runNNN, so its steps resume; any other
tree gets a fresh runNNN. The cdpp run itself holds the config, the Nextflow state and
the driver log.

With ``publish_aretomo3`` the pipeline also lays the refined global reconstruction out as an
AreTomo3 run (the ``aretomo3`` tree, an Embrella AreTomo3 run). A follow-up job, held until the
cdpp job succeeds, makes Embrella's zarr volumes and thumbnails for it, and the AreTomo3 syncer
turns them into review tomograms.
"""

import dataclasses
import json
import logging
import os
import re
import shlex
from typing import Any, Dict, List, Optional, Tuple

from django.utils import timezone
from jinja2 import Environment, FileSystemLoader
from processes.models import JobLog, PipeExecution, PipeInPlan, ProcPlan, ProcRun
from stores.paths import resolve_dir

from common import clusterio
from workflow.agent import RemoteJobSubmitter
from workflow.context import RunContext
from workflow.processors.base import BaseProcessor

logger = logging.getLogger(__name__)

PLAN_SCHEMA = "cdpp.plan/v1"
# Markers so the plan JSON can be pulled out of module/conda noise on stdout.
PLAN_BEGIN = "CDPP_PLAN_BEGIN"
PLAN_END = "CDPP_PLAN_END"
PLAN_TIMEOUT = 180

# Pipeline tree -> the ProcPlan its runs are recorded under.
TREE_PLANS = {
    "miss_alignment": "czii-miss-alignment",
    "isonet2": "czii-isonet2",
    "deepdewedge": "czii-deepdewedge",
    "icecream": "czii-icecream",
    "copick": "czii-copick",
    # Only with publish_aretomo3: the refined reconstruction as an AreTomo3 run.
    "aretomo3": "czii-live",
}

# publish_aretomo3: the round-trip variant the pipeline publishes, and the tree it publishes into.
PUBLISH_VARIANT = "aretomo_recon_from_warp_global"
PUBLISH_TREE = "aretomo3"
_SUBMITTED_JOB = re.compile(r"Submitted batch job (\d+)")

# Shown in a preview, where nothing has been reserved yet.
RESERVED_PLACEHOLDER = "<reserved at submission>"

_SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
_OVERRIDE_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*(\.[A-Za-z0-9_-]+)*")


def parse_overrides(text: Optional[str]) -> List[str]:
    """`key=value` entries of config_overrides: one per line or ';'-separated; blanks and # comments skipped."""
    entries = []
    for line in re.split(r"[\n;]", text or ""):
        entry = line.strip()
        if entry and not entry.startswith("#"):
            entries.append(entry)
    return entries


def publishes_aretomo3(params: Dict[str, Any]) -> bool:
    """The publish_aretomo3 launch option (a JSON boolean, or its string form)."""
    return str(params.get("publish_aretomo3")).strip().lower() in ("true", "1", "yes", "on")


def _between(text: str, begin: str, end: str) -> Optional[str]:
    start = text.find(begin)
    stop = text.find(end, start + len(begin)) if start >= 0 else -1
    return text[start + len(begin) : stop] if start >= 0 and stop >= 0 else None


class CdppProcessor(BaseProcessor):
    """The cdpp pipeline, driven from one long-running SLURM job."""

    name = "cdpp"
    display_name = "CryoET Data Portal Pipeline"
    version = "0.1.0"
    task_name = "cryoet_pipeline"
    # Re-launching a cdpp run resumes it: its execution is restarted in place.
    allows_run_reuse = True

    def validate_parameters(self, params: Dict[str, Any]) -> List[str]:
        errors = []

        aretomo_run = params.get("aretomo_run") or ""
        if not _SAFE_NAME.fullmatch(aretomo_run):
            errors.append("aretomo_run is required and must be a run directory name (e.g. run001)")

        if not _SAFE_NAME.fullmatch(params.get("preset") or ""):
            errors.append("preset is required")

        try:
            if float(params.get("refined_pixel_size")) <= 0:
                errors.append("refined_pixel_size must be positive")
        except (TypeError, ValueError):
            errors.append("refined_pixel_size must be a number")

        for entry in parse_overrides(params.get("config_overrides")):
            key, sep, _ = entry.partition("=")
            if not sep or not _OVERRIDE_KEY.fullmatch(key.strip()):
                errors.append(f"Config override {entry!r} must be dotted.key=value")

        return errors

    # Paths

    def _cdpp_dir(self, run_context: RunContext) -> str:
        """The cdpp run directory: config, Nextflow state, progress.json, driver log."""
        base = self.get_processing_base_path(cluster=run_context.cluster_id)
        return f"{base}/{run_context.msi_session.name}/{run_context.run_number}"

    def _aretomo3_run_dir(self, params: Dict[str, Any], run_context: RunContext) -> str:
        from workflow.processors import get_processor

        base = get_processor("aretomo3").get_processing_base_path(cluster=run_context.cluster_id)
        return f"{base}/{run_context.msi_session.name}/{params['aretomo_run']}"

    def _config_args(self, params: Dict[str, Any], run_context: RunContext) -> List[Tuple[str, str]]:
        """`config from-aretomo3` arguments shared by planning and the job, so the plan is of the config the job writes."""
        args = [
            ("--aretomo3-run", self._aretomo3_run_dir(params, run_context)),
            ("--output-dir", self._cdpp_dir(run_context)),
            ("--session", run_context.msi_session.name),
            ("--preset", params["preset"]),
            ("--refined-pixel-size", str(params["refined_pixel_size"])),
        ]
        if publishes_aretomo3(params):
            args.append(("--publish-aretomo3", PUBLISH_VARIANT))
        args += [("--set", entry) for entry in parse_overrides(params.get("config_overrides"))]
        return args

    # Planning and run reservation

    def plan(self, params: Dict[str, Any], run_context: RunContext) -> Dict[str, Any]:
        """The pipeline's cdpp.plan/v1 document, from a read-only `--plan-only` call over SSH as the service account."""
        env = resolve_dir("cdpp_env", cluster=run_context.cluster_id)
        args = " ".join(f"{flag} {shlex.quote(value)}" for flag, value in self._config_args(params, run_context))
        command = (
            f"module load mamba 2>/dev/null; conda activate {shlex.quote(env)} && "
            f"echo {PLAN_BEGIN} && cryoet-pipeline config from-aretomo3 {args} --plan-only && echo {PLAN_END}"
        )

        ssh = clusterio.get_cluster_ssh_connection(cluster_id=run_context.cluster_id)
        try:
            _, stdout, stderr = ssh.exec_command(command, timeout=PLAN_TIMEOUT)
            out = stdout.read().decode("utf-8", "replace")
            err = stderr.read().decode("utf-8", "replace").strip()
        finally:
            ssh.close()

        block = _between(out, PLAN_BEGIN, PLAN_END)
        if block is None:
            raise ValueError(f"Planning the cdpp run failed: {err[-500:] or 'no plan was printed'}")
        plan = json.loads(block)
        if plan.get("schema") != PLAN_SCHEMA:
            raise ValueError(f"Unexpected cdpp plan schema {plan.get('schema')!r} (expected {PLAN_SCHEMA})")
        return plan

    def reserve_runs(self, run_context: RunContext, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        One runNNN per pipeline tree: reused when an earlier run has the tree's fingerprint, else newly reserved.

        Returns:
            {"trees": {name: {"plan", "run", "dir", "fingerprint", "reused"}}, "pipeline_fingerprint": ...}
        """
        plan = self.plan(params, run_context)
        trees = plan.get("trees") or {}
        unknown = sorted(set(trees) - set(TREE_PLANS))
        if unknown:
            raise ValueError(f"The cdpp plan has trees Embrella has no plan for: {', '.join(unknown)}")

        reserved: Dict[str, Dict[str, Any]] = {}
        try:
            for name, tree in trees.items():
                fingerprint = (tree or {}).get("fingerprint")
                if not fingerprint:
                    # No step of this config writes the tree (e.g. a preset trimmed with overrides):
                    # nothing to reserve, and its roots stay under the cdpp run directory.
                    continue
                reserved[name] = self._reserve_tree(name, fingerprint, run_context)
        except Exception:
            self.release_runs(run_context, {"trees": reserved})
            raise

        return {"trees": reserved, "pipeline_fingerprint": plan.get("fingerprint")}

    def release_runs(self, run_context: RunContext, reservation: Dict[str, Any]) -> None:
        """Delete the tree runs reserve_runs created; reused runs are left alone."""
        for tree in (reservation.get("trees") or {}).values():
            if tree.get("reused"):
                continue
            ProcRun.objects.filter(
                proc_plan__name=tree["plan"],
                msi_session=run_context.msi_session,
                name=tree["run"],
                pipe_executions__isnull=True,
            ).delete()

    def _tree_plan(self, name: str) -> Tuple[ProcPlan, PipeInPlan]:
        plan_name = TREE_PLANS[name]
        step = (
            PipeInPlan.objects.filter(plan__name=plan_name)
            .select_related("plan", "pipe__software")
            .order_by("step", "id")
            .first()
        )
        if step is None:
            raise ValueError(f"Processing plan {plan_name} for the cdpp {name} tree is not configured")
        return step.plan, step

    def _reserve_tree(self, name: str, fingerprint: str, run_context: RunContext) -> Dict[str, Any]:
        from workflow.processors import get_processor
        from workflow.run_numbers import list_run_dirs, reserve_run

        plan, step = self._tree_plan(name)
        session = run_context.msi_session
        base = get_processor(step.pipe.software.processor_class).get_processing_base_path(
            cluster=run_context.cluster_id
        )

        run = self._run_with_fingerprint(plan, session, fingerprint)
        reused = run is not None
        if not reused:
            existing_dirs = list_run_dirs(base, session.name, cluster_id=run_context.cluster_id)
            run = reserve_run(session, plan, existing_dirs=existing_dirs)

        logger.info(f"cdpp {name} tree for {session.name}: {'reusing' if reused else 'reserved'} {run.name}")
        return {
            "plan": plan.name,
            "run": run.name,
            "dir": f"{base}/{session.name}/{run.name}",
            "fingerprint": fingerprint,
            "reused": reused,
        }

    def _run_with_fingerprint(self, plan: ProcPlan, session, fingerprint: str) -> Optional[ProcRun]:
        """The newest run of the plan whose execution recorded this tree fingerprint, or None."""
        executions = (
            PipeExecution.objects.filter(proc_run__proc_plan=plan, proc_run__msi_session=session)
            .select_related("proc_run")
            .order_by("-proc_run__created_at", "-proc_run__id")
        )
        for execution in executions:
            cdpp = (execution.parameters or {}).get("_cdpp") or {}
            if cdpp.get("fingerprint") == fingerprint:
                return execution.proc_run
        return None

    # Script

    def render_script(self, params: Dict[str, Any], run_context: RunContext) -> str:
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        template = Environment(loader=FileSystemLoader(template_dir)).get_template("cdpp.sh.j2")
        context = self.get_template_context(params, run_context)

        reservation = params.get("_reserved_runs") or {}
        trees = [
            {"name": name, "dir": shlex.quote(tree["dir"])} for name, tree in (reservation.get("trees") or {}).items()
        ]
        if not reservation:
            trees = [{"name": "<tree>", "dir": RESERVED_PLACEHOLDER}]

        script = template.render(
            job_name=run_context.job_name,
            slurm_directives=context.get("slurm_directives", []),
            cluster=run_context.cluster_id,
            cdpp_env=shlex.quote(resolve_dir("cdpp_env", cluster=run_context.cluster_id)),
            cdpp_dir=shlex.quote(self._cdpp_dir(run_context)),
            config_args=[(flag, shlex.quote(value)) for flag, value in self._config_args(params, run_context)],
            reserved=bool(reservation),
            trees=trees,
        )
        logger.info(f"Rendered cdpp script for {run_context.msi_session.name}/{run_context.run_number}")
        return script

    # Records

    def on_job_submit(self, run_context: RunContext, job_id: str) -> None:
        """
        Record the job on every tree run, tag the cdpp run's own execution, start the progress syncer.

        The executor has already stored the cdpp run's execution (with the reservation) and
        started the job-status syncer, which updates every execution sharing the job id.
        """
        own = PipeExecution.objects.filter(
            proc_run=run_context.proc_run, pipe_in_plan=run_context.pipe_in_plan, job_id=job_id
        ).first()
        if own is None:
            logger.warning(f"cdpp job {job_id}: no execution record for {run_context.run_number}; trees not recorded")
            return

        reservation = own.parameters.get("_reserved_runs") or {}
        trees = reservation.get("trees") or {}
        cdpp = {
            "pipeline_fingerprint": reservation.get("pipeline_fingerprint"),
            "preset": own.parameters.get("preset"),
            "cdpp_run": run_context.run_number,
        }
        own.parameters = {
            **own.parameters,
            "_cdpp": {
                **cdpp,
                "fingerprint": cdpp["pipeline_fingerprint"],
                "dir": self._cdpp_dir(run_context),
                "trees": {name: tree["run"] for name, tree in trees.items()},
            },
        }
        own.save(update_fields=["parameters", "updated_at"])

        for name, tree in trees.items():
            try:
                if name == PUBLISH_TREE:
                    self._record_published_run(tree, cdpp, own, run_context, job_id)
                else:
                    self._record_tree(name, tree, cdpp, own, run_context, job_id)
            except Exception as e:
                logger.error(f"cdpp job {job_id}: could not record the {name} tree run {tree.get('run')}: {e}")

        self._start_syncer_task(
            syncer_class_path="workflow.processors.cdpp.syncer.CdppSyncer",
            run_context=run_context,
            job_id=job_id,
        )

    def _record_tree(
        self,
        name,
        tree,
        cdpp,
        own: PipeExecution,
        run_context: RunContext,
        job_id: str,
        script_path: Optional[str] = None,
        script_content: Optional[str] = None,
    ) -> None:
        """Create the tree run's execution for job_id, or restart a reused run's in place (script: the cdpp job's)."""
        from workflow.execution import PipelineExecutor

        if script_content is None:
            script_path, script_content = own.script_path, own.script_content

        plan, step = self._tree_plan(name)
        proc_run = (
            ProcRun.objects.filter(proc_plan=plan, msi_session=run_context.msi_session, name=tree["run"])
            .order_by("id")
            .first()
        )
        if proc_run is None:
            raise ValueError(f"run {tree['run']} of {plan.name} is gone")

        parameters = {
            "cluster_id": own.parameters.get("cluster_id"),
            "_cdpp": {**cdpp, "fingerprint": tree["fingerprint"], "tree": name, "dir": tree["dir"]},
        }
        existing = PipeExecution.objects.filter(proc_run=proc_run, pipe_in_plan=step).first()
        if existing:
            PipelineExecutor()._restart_execution(existing, job_id, parameters, script_path, script_content)
            return

        PipeExecution.objects.create(
            proc_run=proc_run,
            pipe_in_plan=step,
            status="submitted",
            job_id=job_id,
            parameters=parameters,
            script_path=script_path,
            script_content=script_content,
            submitted_at=timezone.now(),
        )
        logger.info(f"cdpp job {job_id}: recorded {name} tree run {proc_run.name}")

    # The published AreTomo3 run

    def _record_published_run(self, tree, cdpp, own: PipeExecution, run_context: RunContext, job_id: str) -> None:
        """
        Submit the published run's zarr/thumbnail conversion after the cdpp job; record the run on that job.

        The run's execution follows the conversion job (the AreTomo3 syncer finds its run through
        the execution of the job it watches), so the run counts as done once it can be reviewed.
        """
        try:
            conversion_id, script_path, script = self._submit_conversion(tree, run_context, job_id)
        except Exception as e:
            logger.error(f"cdpp job {job_id}: the published AreTomo3 run {tree['run']} will not be converted: {e}")
            self._record_tree(PUBLISH_TREE, tree, {**cdpp, "conversion_error": str(e)}, own, run_context, job_id)
            return

        cdpp = {**cdpp, "cdpp_job_id": job_id, "conversion_job_id": conversion_id}
        self._record_tree(PUBLISH_TREE, tree, cdpp, own, run_context, conversion_id, script_path, script)
        JobLog.objects.get_or_create(
            job_id=conversion_id,
            defaults={"user": run_context.user, "job_name": self._conversion_job_name(tree, run_context)},
        )

        try:
            from processes.tasks import start_job_status_syncer

            start_job_status_syncer(job_id=conversion_id, cluster_id=run_context.cluster_id)
        except Exception as e:
            logger.warning(f"Error starting the job status syncer for conversion job {conversion_id}: {e}")

        from workflow.processors import get_processor

        self._start_syncer_task(
            syncer_class_path="workflow.processors.aretomo3.syncer.AretomoSyncer",
            run_context=dataclasses.replace(run_context, run_number=tree["run"]),
            job_id=conversion_id,
            base_path=get_processor("aretomo3").get_processing_base_path(cluster=run_context.cluster_id),
        )

    def _conversion_job_name(self, tree, run_context: RunContext) -> str:
        return f"aretomo3_{run_context.msi_session.name}_{tree['run']}_cdpp_convert"

    def render_conversion_script(self, tree, run_context: RunContext, cdpp_job_id: str) -> str:
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        template = Environment(loader=FileSystemLoader(template_dir)).get_template("cdpp_publish_convert.sh.j2")
        return template.render(
            job_name=self._conversion_job_name(tree, run_context),
            cdpp_job_id=cdpp_job_id,
            run_dir=shlex.quote(tree["dir"]),
            software_root=shlex.quote(self.get_software_root(cluster=run_context.cluster_id)),
            cluster=run_context.cluster_id,
        )

    def _submit_conversion(self, tree, run_context: RunContext, cdpp_job_id: str) -> Tuple[str, str, str]:
        """sbatch the conversion as the launching user, held until the cdpp job succeeds. Returns (job id, path, script)."""
        auth, error = clusterio.get_auth_for_user(run_context.user, run_context.cluster_id)
        if error:
            raise ValueError(error.get("error") or str(error))

        script = self.render_conversion_script(tree, run_context, cdpp_job_id)
        submitter = RemoteJobSubmitter(
            cluster_id=run_context.cluster_id,
            auth=auth,
            remote_script_dir=self.get_script_directory(cluster=run_context.cluster_id),
        )
        try:
            submitter.connect()
            output, stderr = submitter.run_script(
                script_content=script, job_name=self._conversion_job_name(tree, run_context)
            )
        finally:
            submitter.close()

        match = _SUBMITTED_JOB.search(output or "")
        if not match:
            raise ValueError(f"sbatch printed no job id: {(stderr or output or '').strip()[-300:]}")
        logger.info(f"cdpp job {cdpp_job_id}: conversion of the published AreTomo3 run {tree['run']} is job {match[1]}")
        return match[1], submitter.last_script_path, script

    def on_job_complete(self, run_context: RunContext, success: bool) -> None:
        logger.info(f"cdpp job for {run_context.msi_session.name}/{run_context.run_number} complete: success={success}")


# Register the processor after the class is fully defined to avoid circular imports
from workflow.processors import register_processor  # noqa: E402

register_processor(CdppProcessor)
