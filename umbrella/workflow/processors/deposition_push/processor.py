"""DepositionPushProcessor - Runs one SLURM job that uploads a prep-staged dataset to S3 Portal.
``aws s3 sync`` of the dataset subtree; mirrors ``cryoetportalprep push``.
"""

import logging
import os
import shlex
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader

from workflow.context import RunContext
from workflow.processors import register_processor
from workflow.processors.base import BaseProcessor

logger = logging.getLogger(__name__)

REQUIRED_PARAMS = ("staged_dir", "s3_dest")
# Software setup before the sync; one command per line so set -e catches a failed load.
DEFAULT_PROLOGUE = "ml load anaconda\nconda activate dataportalenv\nml load awscli"
# Local-only artifacts kept out of the upload (mirrors cryoetportalprep SYNC_EXCLUDE_PATTERNS).
EXCLUDE_PATTERNS = [
    "dataprep_config.yaml",
    "sync_job.sh",
    "cryoetprep_push_*",
    "notes.md",
    ".venv/*",
    "__pycache__/*",
    "*.pyc",
    ".pytest_cache/*",
]


class DepositionPushProcessor(BaseProcessor):
    name = "deposition-push"
    display_name = "Deposition Push"
    version = "0.1.0"
    cluster = "bruno"
    allowed_clusters = ["bruno", "czii"]
    task_name = "deposition_push"
    hidden_from_list = True

    def validate_parameters(self, params: Dict[str, Any]) -> List[str]:
        return [f"{key} is required" for key in REQUIRED_PARAMS if not params.get(key)]

    def render_script(self, params: Dict[str, Any], run_context: RunContext) -> str:
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("deposition_push.sh.j2")
        return template.render(
            staged_dir=shlex.quote(params["staged_dir"]),
            s3_dest=shlex.quote(params["s3_dest"]),
            prologue=params.get("prologue", DEFAULT_PROLOGUE),
            exclude_patterns=EXCLUDE_PATTERNS,
            cluster=run_context.cluster_id,
            slurm_directives=self.generate_slurm_directives(params),
        )

    def on_job_submit(self, run_context: RunContext, job_id: str) -> None:
        # Unused for deposition jobs: the submit service starts the DatasetJob syncer after launch.
        logger.info("Deposition push job %s submitted", job_id)

    def on_job_complete(self, run_context: RunContext, success: bool) -> None:
        logger.info("Deposition push job complete: success=%s", success)


register_processor(DepositionPushProcessor)
