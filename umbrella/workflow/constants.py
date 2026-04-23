"""Workflow-level constants that must be importable without triggering
`workflow.views.__init__`. Keep this file dependency-free.
"""

# Default cluster for runs/jobs that don't carry an explicit cluster_id.
DEFAULT_CLUSTER_ID = "czii"
