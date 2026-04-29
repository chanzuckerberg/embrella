#!/bin/bash
# =============================================================================
# Launch Nextflow locally to orchestrate cross-cluster jobs via SSH.
#
# Usage:
#   bash run.sh /path/to/aretomo3_job.sh /path/to/copick_job.sh
#
# What happens:
#   1. Nextflow runs locally and submits AreTomo3 to CZII via SSH
#   2. Waits 20 minutes after AreTomo3 completes
#   3. Submits Copick Create Project to Bruno via SSH
#   4. Reports and timeline saved to reports/
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARETOMO3_SCRIPT="${1:?Usage: bash run.sh /path/to/aretomo3_job.sh /path/to/copick_job.sh}"
COPICK_SCRIPT="${2:?Usage: bash run.sh /path/to/copick.sh /path/to/copick_job.sh}"

echo "============================================"
echo "Nextflow Cross-Cluster Workflow"
echo "============================================"
echo "Pipeline:       ${SCRIPT_DIR}/main.nf"
echo "Config:         ${SCRIPT_DIR}/nextflow.config"
echo "AreTomo3 script: ${ARETOMO3_SCRIPT}"
echo "Copick script:   ${COPICK_SCRIPT}"
echo "Reports:        ${SCRIPT_DIR}/reports/"
echo "============================================"

mkdir -p "${SCRIPT_DIR}/reports"

cd "${SCRIPT_DIR}"
nextflow run main.nf \
    --aretomo3_script "${ARETOMO3_SCRIPT}" \
    --copick_script "${COPICK_SCRIPT}" \
    -resume
