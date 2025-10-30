#!/bin/bash

#SBATCH --job-name=copick_membraneseg
#SBATCH --time=72:00:00
#SBATCH --partition=gpu
#SBATCH --gpus=4
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=32G

ml anaconda
conda activate /hpc/projects/group.czii/conda_environments/pyczii

#initialize required parameters
session="{{ session }}"
copick_procrun="{{ copickRun }}"

tomo_alg = "{{ tomoType }}"
tomo_voxelsize = {{ tomoVoxelSize }}
membraneseg_session_id = "{{ sessionID }}"

# optional parameters
threshold="{{ threshold }}"
# dynamic parameters based
copick_dir="/hpc/projects/group.czii/krios1.processing/copick/${session}/${copick_procrun}"

mkdir -p "${copick_dir}"

# --- dynamically set log paths for this job ---
JOBTAG="${session}_${membraneseg_session_id}_${SLURM_JOB_ID:-$$}"
LOG_OUT="${copick_dir}/copick_run_membrane_${JOBTAG}.out"
LOG_ERR="${copick_dir}/copick_run_membrane_${JOBTAG}.err"
exec >"${LOG_OUT}" 2>"${LOG_ERR}"

# --- dynamically send email notifications ---
EMAIL_DOMAIN="czii.org"
MAIL_TO="${SLURM_JOB_USER:-$USER}@${EMAIL_DOMAIN}"

if [[ -n "${SLURM_JOB_ID:-}" ]]; then
  scontrol update JobId=${SLURM_JOB_ID} MailUser=${MAIL_TO} MailType=BEGIN,END,FAIL
fi

# build cmd
is_number() {
  [[ "$1" =~ ^[0-9]+([.][0-9]+)?$ ]]
}

# base cmd
cmd=(copick inference membrain-seg
  --config "${copick_dir}/config.json"
  --tomo-alg "${tomo_alg}"
  --voxel-size "${tomo_voxelsize}"
  --session-id "${membraneseg_session_id}"
)

# Append threshold only if valid numeric float
if [[ -n "${threshold}" && "${threshold}" != "{{ threshold }}" ]]; then
  if is_number "${threshold}"; then
    cmd+=("--threshold" "${threshold}")
  else
    echo "Warning: threshold '${threshold}' is not numeric; skipping." >&2
  fi
fi

echo "Running:" "${cmd[@]}"
"${cmd[@]}"
