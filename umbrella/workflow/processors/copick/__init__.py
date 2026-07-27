"""Copick Processor Package."""

from workflow.processors.copick.add_object_processor import CopickAddObjectProcessor
from workflow.processors.copick.import_processor import CopickImportProcessor
from workflow.processors.copick.processor import CopickProcessor

__all__ = ["CopickProcessor", "CopickAddObjectProcessor", "CopickImportProcessor"]
