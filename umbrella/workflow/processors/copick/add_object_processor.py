"""
Copick Add Object processor for the generic pipeline execution system.

This processor handles adding pickable object definitions to existing Copick projects.
It is a subclass of CopickProcessor that only supports the add_object operation.
"""

from typing import Any, Dict, List

from workflow.processors import register_processor
from workflow.processors.copick import views
from workflow.processors.copick.processor import CopickProcessor


class CopickAddObjectProcessor(CopickProcessor):
    """
    Copick Add Object processor for adding pickable objects to existing projects.

    This processor creates ProcRun records with the copick-add-object plan,
    allowing multiple objects to be added to the same Copick project with
    proper tracking via standard run### naming pattern.
    """

    name = "copick-add-object"
    display_name = "Copick Add Object"
    version = "1.0"
    task_name = "copick_add_object"

    # Hidden from processor dropdown - accessed via Copick form's Add Object tab
    hidden_from_list = True

    @classmethod
    def get_views_module(cls):
        """
        Get the views module for this processor.

        Returns the parent copick views module since add_object shares
        the same API endpoints (options, validation, defaults, metadata).
        """
        return views

    def validate_parameters(self, params: Dict[str, Any]) -> List[str]:
        """
        Validate parameters for add_object operation only.

        Args:
            params: Parameter dictionary

        Returns:
            List of error messages (empty if valid)
        """
        # Only allow add_object operation
        if params.get("operation") != "add_object":
            return ["copick-add-object processor only supports add_object operation"]

        # Delegate to parent for add_object-specific validation
        return super().validate_parameters(params)


# Register the processor after the class is fully defined
register_processor(CopickAddObjectProcessor)
