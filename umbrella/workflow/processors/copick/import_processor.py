"""
Copick Import processor for the generic pipeline execution system.

This processor handles importing tomograms to existing Copick projects.
It is a subclass of CopickProcessor that only supports the import_tomograms operation.
"""

from typing import Any, Dict, List

from workflow.processors import register_processor
from workflow.processors.copick import views
from workflow.processors.copick.processor import CopickProcessor


class CopickImportProcessor(CopickProcessor):
    """
    Copick Import processor for importing tomograms to existing projects.

    This processor creates ProcRun records with the copick-import plan,
    allowing multiple import operations to the same Copick project with
    proper tracking via standard run### naming pattern.
    """

    name = "copick-import"
    display_name = "Copick Import"
    version = "1.0.1"
    task_name = "copick_import"

    # Hidden from processor dropdown - accessed via Copick form's Import Tomograms tab
    hidden_from_list = True

    def get_processing_base_path(self) -> str:
        """
        Get the base processing path for this processor.

        Uses the parent copick processor's path since import is an
        accessory action that shares the same script directory.

        Returns:
            /hpc/projects/group.czii/krios1.processing/copick
        """
        return "/hpc/projects/group.czii/krios1.processing/copick"

    @classmethod
    def get_views_module(cls):
        """
        Get the views module for this processor.

        Returns the parent copick views module since import shares
        the same API endpoints (options, validation, defaults, metadata).
        """
        return views

    def validate_parameters(self, params: Dict[str, Any]) -> List[str]:
        """
        Validate parameters for import_tomograms operation only.

        Args:
            params: Parameter dictionary

        Returns:
            List of error messages (empty if valid)
        """
        # Only allow import_tomograms operation
        if params.get("operation") != "import_tomograms":
            return ["copick-import processor only supports import_tomograms operation"]

        # Delegate to parent for import_tomograms-specific validation
        return super().validate_parameters(params)


# Register the processor after the class is fully defined
register_processor(CopickImportProcessor)
