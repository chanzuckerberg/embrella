"""
Progress syncer for cdpp runs.

The cdpp job refreshes ``<cdpp run>/nextflow/progress.json`` (a ``cdpp.progress/v1``
document) while its driver runs; every iteration this syncer reads it and logs a
one-line summary. Tomogram records are not created here: the tool trees are recorded as
ProcRuns at submission, and their status follows the driver job.
"""

import json

from processes.models import PipeExecution

from common import clusterio
from workflow import syncers
from workflow.syncers import log

PROGRESS_SCHEMA = "cdpp.progress/v1"


def summarize_progress(document: dict) -> tuple[str, dict]:
    """(one-line message, metadata) for a cdpp.progress/v1 document."""
    summary = document.get("summary") or {}
    failed_steps = [step["name"] for step in document.get("steps") or [] if (step.get("counts") or {}).get("failed")]
    message = (
        f"Pipeline progress: {summary.get('done', 0)}/{summary.get('total', 0)} done, "
        f"{summary.get('running', 0)} running, {summary.get('queued', 0)} queued, {summary.get('failed', 0)} failed"
    )
    if failed_steps:
        message += f" ({', '.join(failed_steps)})"
    metadata = {
        "summary": summary,
        "failed_steps": failed_steps,
        "generated_at": document.get("generated_at"),
        "driver_job_id": (document.get("submission") or {}).get("driver_job_id"),
    }
    return message, metadata


class CdppSyncer(syncers.ProcessSyncer):
    processor_name = "cdpp"

    def setup(self, run_id, session_name, cluster_id=None):
        super().setup(run_id=run_id, session_name=session_name, cluster_id=cluster_id)
        if not self.job_id:
            return

        # The driver job also backs the tree runs' executions; log against the cdpp run's own.
        own = PipeExecution.objects.filter(
            job_id=self.job_id,
            proc_run__name=run_id,
            proc_run__msi_session__name=session_name,
            pipe_in_plan__pipe__software__processor_class=self.processor_name,
        ).first()
        if own is None or own == self._pipe_execution:
            return
        self._pipe_execution = own
        if self._syncer_process:
            self._syncer_process.pipe_execution = own
            self._syncer_process.save(update_fields=["pipe_execution"])

    def sync_results(self):
        path = f"{self.session_path}/nextflow/progress.json"
        try:
            document = json.loads(clusterio.read_remote_file(self.cluster_id, path))
        except FileNotFoundError:
            self._log_to_db("warning", f"No progress yet: {path} does not exist", {"path": path})
            return
        except ValueError as e:
            self._log_to_db("warning", f"Unreadable progress file {path}: {e}", {"path": path})
            return

        if document.get("schema") != PROGRESS_SCHEMA:
            self._log_to_db(
                "warning",
                f"Unexpected progress schema {document.get('schema')!r} in {path}",
                {"path": path, "schema": document.get("schema")},
            )
            return

        message, metadata = summarize_progress(document)
        log.info(f"{self.session_name}/{self.run_id}: {message}")
        self._log_to_db("sync_complete", message, metadata)
