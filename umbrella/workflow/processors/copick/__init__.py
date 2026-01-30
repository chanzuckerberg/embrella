"""Copick Processor Package."""

from workflow.processors.copick.processor import CopickProcessor
from workflow.processors.copick.add_object_processor import CopickAddObjectProcessor
from workflow.processors.copick.import_processor import CopickImportProcessor

__all__ = ["CopickProcessor", "CopickAddObjectProcessor", "CopickImportProcessor"]
