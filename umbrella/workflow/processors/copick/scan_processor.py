"""Copick scan processor — read-only enumeration of picks/segmentations/meshes."""

import logging
import os
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader
from stores.paths import resolve_dir

from workflow.context import RunContext
from workflow.processors import get_processor, register_processor

from .processor import CopickProcessor

logger = logging.getLogger(__name__)


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
        return []

    def _copick_dir(self, run_context: RunContext) -> str:
        base = get_processor("copick").get_processing_base_path(cluster=run_context.cluster_id)
        return f"{base}/{run_context.msi_session.name}/{run_context.run_number}"

    def render_script(self, params: Dict[str, Any], run_context: RunContext) -> str:
        copick_dir = self._copick_dir(run_context)
        context = self.get_template_context(params, run_context)

        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("copick_scan.sh.j2")

        script = template.render(
            configPath=f"{copick_dir}/config.json",
            scanOutPath=f"{copick_dir}/scan.json",
            copickEnv=resolve_dir("dataportal_env", cluster=run_context.cluster_id),
            session=run_context.msi_session.name,
            run=run_context.run_number,
            slurm_directives=context.get("slurm_directives", []),
        )
        logger.info("Rendered copick scan script for %s/%s", run_context.msi_session.name, run_context.run_number)
        return script


register_processor(CopickScanProcessor)
