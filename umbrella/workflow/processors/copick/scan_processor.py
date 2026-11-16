"""Copick scan processor — read-only enumeration of picks/segmentations/meshes."""

import json
import logging
import os
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader
from stores.paths import resolve_dir

from workflow.context import RunContext
from workflow.processors import get_processor, register_processor

from .processor import CopickProcessor

logger = logging.getLogger(__name__)


def _validate_dataset_id(raw) -> int:
    """Positive int only: the value lands in a cluster path and the sbatch script."""
    if isinstance(raw, (bool, float)):  # int() would coerce True and 7.9
        raise ValueError(f"dataset_id must be a positive integer, got {raw!r}.")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 0
    if value <= 0:
        raise ValueError(f"dataset_id must be a positive integer, got {raw!r}.")
    return value


class CopickScanProcessor(CopickProcessor):
    """Enumerate a copick project's annotations and write an aggregated scan.json."""

    name = "copick-scan"
    display_name = "Copick Scan"
    task_name = "copick_scan"
    # Internal read job triggered by the deposition flow, not a user-launchable.
    hidden_from_list = True

    def get_parameter_schema(self) -> Dict[str, Any]:
        """No user inputs — session/run come from the run context, env from the paths API."""
        return {
            "type": "object",
            "properties": {
                "slurm_partition": {"type": "string", "default": "cpu", "x-slurm-directive": "--partition"},
                "slurm_cpus_per_task": {"type": "integer", "default": 4, "x-slurm-directive": "--cpus-per-task"},
                "slurm_mem_per_cpu": {"type": "string", "default": "8G", "x-slurm-directive": "--mem-per-cpu"},
                "slurm_time": {"type": "string", "default": "00:30:00", "x-slurm-directive": "--time"},
            },
        }

    def validate_parameters(self, params: Dict[str, Any]) -> List[str]:
        try:
            _validate_dataset_id(params.get("dataset_id"))
        except ValueError as e:
            return [str(e)]
        return []

    def _copick_dir(self, run_context: RunContext) -> str:
        base = get_processor("copick").get_processing_base_path(cluster=run_context.cluster_id)
        return f"{base}/{run_context.msi_session.name}/{run_context.run_number}"

    def render_script(self, params: Dict[str, Any], run_context: RunContext) -> str:
        dataset_id = _validate_dataset_id(params.get("dataset_id"))
        copick_dir = self._copick_dir(run_context)
        context = self.get_template_context(params, run_context)

        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("copick_scan.sh.j2")

        # Empty positions scan the whole project.
        scan_positions = [name for name in (params.get("scan_positions") or []) if name]
        script = template.render(
            configPath=f"{copick_dir}/config.json",
            scanOutPath=f"{copick_dir}/scan-{dataset_id}.json",
            copickEnv=resolve_dir("dataportal_env", cluster=run_context.cluster_id),
            session=run_context.msi_session.name,
            run=run_context.run_number,
            scanPositions=json.dumps(scan_positions),
            slurm_directives=context.get("slurm_directives", []),
        )
        logger.info("Rendered copick scan script for %s/%s", run_context.msi_session.name, run_context.run_number)
        return script


register_processor(CopickScanProcessor)
