"""
CryoET Data Portal Pipeline (cdpp) processor module.

Runs the cdpp Nextflow pipeline on an AreTomo3 run, writing into Embrella's per-tool trees.
"""

from .processor import CdppProcessor

__all__ = ["CdppProcessor"]
