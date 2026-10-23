"""DepositionPrepProcessor - Runs one SLURM job to stage and validate a dataset before the push.
``sync -> pre-flight validation (push --dry-run, scoped to this dataset)``
"""

import logging
import os
import shlex
from pathlib import Path
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
    task_name = "deposition_prep"
    hidden_from_list = True

    def validate_parameters(self, params: Dict[str, Any]) -> List[str]:
        errors = [
            f"{key} is required"
            for key in ("output_dir", "config_path", "config_yaml", "dataset_id")
            if not params.get(key)
        ]
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
            progress_code=(Path(__file__).parent.parent / "deposition_progress.py").read_text(),
            validation_code=(Path(__file__).parent.parent / "deposition_validation.py").read_text(),
            dataset_id=shlex.quote(str(params["dataset_id"])),
            output_dir=shlex.quote(params["output_dir"]),
            config_path=shlex.quote(params["config_path"]),
            config_yaml=config_yaml,
            config_delimiter=config_delimiter,
            session_flags=session_flags,
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
