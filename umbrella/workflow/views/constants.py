"""
Module-level constants for workflow views.
"""

# AreTomo3 Parameter Keys
KEYS = (
    "PixSize",
    "SplitSum",
    "Resume",
    "EerSampling",
    "McPatch",
    "Cmd",
    "McIter",
    "Group",
    "RotGain",
    "FlipGain",
    "InvGain",
    "TotalDose",
    "AlignZ",
    "VolZ",
    "ExtZ",
    "AtBin",
    "TiltAxis",
    "TiltCor",
    "AtPatch",
    "OutImod",
    "ExtPhase",
    "CorrCTF",
    "McBin",
    "Wbp",
)

# SLURM Status Mappings
SLURM_STATE_TO_LABEL = {
    "RUNNING": "Running",
    "PENDING": "Pending",
    "COMPLETING": "Completing",
    "COMPLETED": "Completed",
    "FAILED": "Failed",
    "CANCELLED": "Cancelled",
    "TIMEOUT": "Timeout",
}

# Reverse mapping: label to SLURM state
LABEL_TO_SLURM_STATE = {v: k for k, v in SLURM_STATE_TO_LABEL.items()}
