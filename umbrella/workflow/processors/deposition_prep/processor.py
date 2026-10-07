"""DepositionPrepProcessor - Runs one SLURM job to stage and validates a dataset before the push.
``sync -> copick deposit -> push --dry-run``
"""

import logging
import os
import shlex
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader
from stores.paths import resolve_dir

from workflow.context import RunContext
from workflow.processors import register_processor
from workflow.processors.base import BaseProcessor

logger = logging.getLogger(__name__)


class DepositionPrepProcessor(BaseProcessor):
    name = "deposition-prep"
    display_name = "Deposition Prep"
    version = "0.1.0"
    cluster = "bruno"
    allowed_clusters = ["bruno", "czii"]
    task_name = "deposition_prep"
    hidden_from_list = True

    def validate_parameters(self, params: Dict[str, Any]) -> List[str]:
        errors = [f"{key} is required" for key in ("output_dir", "config_path", "config_yaml") if not params.get(key)]
        if params.get("copick_flags") and not (params.get("copick_config") and params.get("target_dir")):
            errors.append("copick_config and target_dir are required when annotations are selected")
        return errors

    def render_script(self, params: Dict[str, Any], run_context: RunContext) -> str:
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("deposition_prep.sh.j2")
        prep_env = params.get("prep_env") or resolve_dir("dataportal_env", cluster=run_context.cluster_id)
        # Scope sync to this dataset's sessions; blank means process the whole config.
        session_flags = "".join(f" -s {shlex.quote(name)}" for name in params.get("session_names") or [])
        config_yaml = params["config_yaml"]
        config_delimiter = "END_CONFIG"
        while config_delimiter in config_yaml.splitlines():
            config_delimiter += "_"
        return template.render(
            output_dir=shlex.quote(params["output_dir"]),
            config_path=shlex.quote(params["config_path"]),
            config_yaml=config_yaml,
            config_delimiter=config_delimiter,
            copick_config=shlex.quote(params.get("copick_config", "")),
            target_dir=shlex.quote(params.get("target_dir", "")),
            copick_flags=params.get("copick_flags", ""),  # Caller must shell-quote each value.
            session_flags=session_flags,
            # Gates the whole-config `push --dry-run`. The submit flow leaves it off per dataset;
            run_validate=params.get("run_validate", True),
            prep_env=shlex.quote(prep_env),
            cluster=run_context.cluster_id,
            slurm_directives=self.generate_slurm_directives(params),
        )

    def on_job_submit(self, run_context: RunContext, job_id: str) -> None:
        # Unused for deposition jobs: the submit service starts the DatasetJob syncer after launch.
        logger.info("Deposition prep job %s submitted", job_id)

    def on_job_complete(self, run_context: RunContext, success: bool) -> None:
        logger.info("Deposition prep job complete: success=%s", success)


register_processor(DepositionPrepProcessor)
