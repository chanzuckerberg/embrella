"""
Output-only processors.

Hidden, never-launched processors for tools whose runs an external pipeline produces.
"""

from .processor import DeepDeWedgeProcessor, IcecreamProcessor, IsoNet2Processor, MissAlignmentProcessor

__all__ = ["MissAlignmentProcessor", "IsoNet2Processor", "DeepDeWedgeProcessor", "IcecreamProcessor"]
