"""
Processor Registry and Base Classes

This module provides the registration system for processing software integrations.
Each processor handles job submission, parameter validation, and output tracking
for a specific software package (e.g., AreTomo3, DenoisET, CryoSPARC).

Usage:
    from workflow.processors import register_processor, get_processor
    from workflow.processors.base import BaseProcessor

    @register_processor
    class MyProcessor(BaseProcessor):
        name = "my_software"
        # ... implementation

    # Later, get the processor:
    processor = get_processor("my_software")
"""

from typing import TYPE_CHECKING, Dict, Type

if TYPE_CHECKING:
    from .base import BaseProcessor

# Global registry mapping processor names to classes
_PROCESSOR_REGISTRY: Dict[str, Type["BaseProcessor"]] = {}

from .base import BaseProcessor  # noqa: E402


def register_processor(cls: Type[BaseProcessor]) -> Type[BaseProcessor]:
    """
    Decorator to register a processor class in the global registry.

    Args:
        cls: Processor class to register (must subclass BaseProcessor)

    Returns:
        The class (unchanged)

    Raises:
        ValueError: If class doesn't define 'name' attribute or name already registered

    Example:
        @register_processor
        class AreTomo3Processor(BaseProcessor):
            name = "aretomo3"
            # ... implementation
    """
    if not hasattr(cls, "name") or cls.name is None:
        raise ValueError(
            f"{cls.__name__} must define a 'name' class attribute. Example: name = 'aretomo3'",
        )

    if cls.name in _PROCESSOR_REGISTRY:
        existing = _PROCESSOR_REGISTRY[cls.name]
        raise ValueError(
            f"Processor name '{cls.name}' is already registered by {existing.__name__}. "
            f"Cannot register {cls.__name__}.",
        )

    _PROCESSOR_REGISTRY[cls.name] = cls
    return cls


def get_processor(name: str) -> BaseProcessor:
    """
    Get a processor instance by name.

    Args:
        name: Processor name (e.g., "aretomo3")

    Returns:
        Instance of the processor class

    Raises:
        ValueError: If processor name not found in registry

    Example:
        processor = get_processor("aretomo3")
        schema = processor.get_parameter_schema()
    """
    if name not in _PROCESSOR_REGISTRY:
        available = ", ".join(sorted(_PROCESSOR_REGISTRY.keys()))
        raise ValueError(
            f"Unknown processor: '{name}'. Available processors: {available if available else 'none'}",
        )

    processor_class = _PROCESSOR_REGISTRY[name]
    return processor_class()


def list_processors() -> Dict[str, Type[BaseProcessor]]:
    """
    Get all registered processors.

    Returns:
        Dictionary mapping processor names to their classes

    Example:
        processors = list_processors()
        for name, cls in processors.items():
            print(f"{name}: {cls.display_name}")
    """
    return _PROCESSOR_REGISTRY.copy()


# Import processor implementations after all functions are defined
# to allow clean registration without circular imports
from . import (  # noqa: E402, F401
    aretomo3,
    copick,
    denoiset,
    deposition_prep,
    membraneseg,
)
