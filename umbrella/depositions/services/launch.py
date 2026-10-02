"""Launch a deposition prep/push processor as a one-off SLURM job.
"""

import logging
import re
from dataclasses import dataclass

from workflow.agent import RemoteJobSubmitter
from workflow.processors import get_processor

logger = logging.getLogger(__name__)

_JOB_ID_RE = re.compile(r"Submitted batch job (\d+)")


@dataclass
class DepositionRunContext:
    # Deposition processors only read cluster_id off the context.
    cluster_id: str


def launch_deposition_job(*, processor_name, params, cluster_id, job_name, auth=None):
    """Render the processor's script, sbatch it, and return the SLURM job id."""
    processor = get_processor(processor_name)
    script = processor.render_script(params, DepositionRunContext(cluster_id=cluster_id))
    submitter = RemoteJobSubmitter(
        cluster_id=cluster_id,
        auth=auth,
        remote_script_dir=processor.get_script_directory(cluster=cluster_id),
    )
    try:
        submitter.connect()
        output, error = submitter.run_script(script_content=script, job_name=job_name)
        if error:
            logger.warning("SLURM stderr for %s: %s", job_name, error)
        match = _JOB_ID_RE.search(output or "")
        if not match:
            raise ValueError(f"Could not parse SLURM job id from sbatch output: {output!r} (stderr: {error!r})")
        job_id = match.group(1)
        logger.info("Launched %s as SLURM job %s on %s", job_name, job_id, cluster_id)
        return job_id
    finally:
        submitter.close()
