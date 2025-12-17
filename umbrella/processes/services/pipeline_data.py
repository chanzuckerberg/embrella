"""
Pipeline data service for managing RunPipeData records and output paths.

This service encapsulates business logic for creating and managing pipeline
data outputs, previously embedded in the ProcRun model.
"""
from stores.models import Path, fill_place_holders
from processes.models import PipeInPlan, RunPipeData


class PipelineDataService:
    """Service for managing pipeline data and output path generation."""

    @staticmethod
    def save_pipe_run_data(proc_run):
        """
        Create RunPipeData records for all outputs in the processing plan.

        Creation of ProcRun instance triggers saving of pipe_run_data which are
        output data of the run.

        Args:
            proc_run: ProcRun instance

        Returns:
            List of created RunPipeData instances
        """
        pipes_in_plan = PipeInPlan.objects.filter(plan=proc_run.proc_plan)
        created_data = []

        for pp in pipes_in_plan:
            p = pp.pipe
            for p_out in p.output.all():
                # create pipe_run_data for each of the output.
                replacement_map = pp.get_replacement_map(
                    proc_run=proc_run,
                    msi_session=proc_run.msi_session,
                )

                out_static = fill_place_holders(
                    p_out.static_path.static_path,
                    replacement_map,
                )
                out_overlay = fill_place_holders(
                    p_out.overlay_path,
                    replacement_map,
                )

                out_path = Path.objects.create(
                    static_path=out_static,
                    overlay_path=out_overlay,
                )

                data_instance = RunPipeData.objects.create(
                    run=proc_run,
                    pipe=p,
                    pathtype=p_out,
                    path=out_path,
                )
                created_data.append(data_instance)

        return created_data
