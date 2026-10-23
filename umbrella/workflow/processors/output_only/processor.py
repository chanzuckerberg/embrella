"""
Output-only processors.

Tools run by an external pipeline rather than launched from Embrella. Registering
them gives each tool a ProcSoftware row (and so a processing root) and a ProcPlan,
so its run directories, {processing_root}/{proc_software}/{session}/{runNNN}, can
be recorded as ProcRuns like any other software's. They are hidden from the launch
list and refuse to render a script.
"""

from typing import Any, Dict, List

from workflow.context import RunContext
from workflow.processors import register_processor
from workflow.processors.base import BaseProcessor


class OutputOnlyProcessor(BaseProcessor):
    """Base for software whose runs another pipeline produces."""

    # The tool version is recorded by the pipeline that runs it.
    version = "external"
    hidden_from_list = True

    def _not_launchable(self) -> str:
        return (
            f"{self.display_name} runs are produced by an external pipeline; "
            f"'{self.name}' cannot be launched from Embrella."
        )

    def get_parameter_schema(self) -> Dict[str, Any]:
        """No parameters: nothing is ever rendered."""
        return {"type": "object", "properties": {}}

    def validate_parameters(self, params: Dict[str, Any]) -> List[str]:
        return [self._not_launchable()]

    def render_script(self, params: Dict[str, Any], run_context: RunContext) -> str:
        raise NotImplementedError(self._not_launchable())

    def on_job_submit(self, run_context: RunContext, job_id: str) -> None:
        pass

    def on_job_complete(self, run_context: RunContext, success: bool) -> None:
        pass


class MissAlignmentProcessor(OutputOnlyProcessor):
    name = "miss_alignment"
    display_name = "Miss-alignment refinement"
    task_name = "alignment_refinement"


class IsoNet2Processor(OutputOnlyProcessor):
    name = "isonet2"
    display_name = "IsoNet2"
    task_name = "missing_wedge_correction"


class DeepDeWedgeProcessor(OutputOnlyProcessor):
    name = "deepdewedge"
    display_name = "DeepDeWedge"
    task_name = "missing_wedge_correction"


class IcecreamProcessor(OutputOnlyProcessor):
    name = "icecream"
    display_name = "ICECREAM"
    task_name = "missing_wedge_correction"


for _processor in (MissAlignmentProcessor, IsoNet2Processor, DeepDeWedgeProcessor, IcecreamProcessor):
    register_processor(_processor)
