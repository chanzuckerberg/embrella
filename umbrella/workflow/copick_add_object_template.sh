#!/bin/bash

#SBATCH --job-name=add_object_particle
#SBATCH --time=30:00
#SBATCH --partition=gpu
#SBATCH --gpus=1
#SBATCH --mem-per-cpu=196G


ml anaconda
conda activate /hpc/projects/group.czii/conda_environments/pyczii

#initialize parameters
session="{{ session }}"
copick_procrun="{{ copickRun }}"
object_name="{{ objectName }}"
object_diameter="{{ objectDiameter }}"
#initializing parameters end

# optional fields
pdb_id="{{ pdbID }}"
object_volume="{{ objectMapFile }}"
object_voxel_size="{{ objectVoxelSize }}"

# Dynamic variables
copick_dir="/hpc/projects/group.czii/krios1.processing/copick/${session}/${copick_procrun}"
radius="$(echo "${object_diameter} / 2" | bc -l)"

mkdir -p "${copick_dir}"

# --- dynamically set log paths for this job ---
JOBTAG="${session}_${copick_procrun}_${SLURM_JOB_ID:-$$}"
LOG_OUT="${copick_dir}/add_object_${JOBTAG}.out"
LOG_ERR="${copick_dir}/add_object_${JOBTAG}.err"
exec >"${LOG_OUT}" 2>"${LOG_ERR}"

# --- dynamically send email notifications ---
EMAIL_DOMAIN="czii.org"
MAIL_TO="${SLURM_JOB_USER:-$USER}@${EMAIL_DOMAIN}"

if [[ -n "${SLURM_JOB_ID:-}" ]]; then
  scontrol update JobId=${SLURM_JOB_ID} MailUser=${MAIL_TO} MailType=BEGIN,END,FAIL
fi

# compose base command
is_number() {
  [[ $1 =~ ^[0-9]+([.][0-9]+)?$ ]]
}
cmd="copick add object \
  --config \"${copick_dir}/config.json\" \
  --name \"${object_name}\" \
  --object-type particle \
  --radius ${radius}"

# Optional: pdb-id
if [[ -n "$pdb_id" && "$pdb_id" != "NA" && "$pdb_id" != "{{ pdbID }}" ]]; then
  cmd+=" --pdb-id \"$pdb_id\""
fi

# Optional: volume (absolute path already provided)
if [[ -n "$object_volume" && "$object_volume" != "{{ objectMapFile }}" ]]; then
  cmd+=" --volume \"$object_volume\""
fi

# Optional: voxel size (must be numeric)
if [[ -n "$object_voxel_size" && "$object_voxel_size" != "{{ objectVoxelSize }}" ]]; then
  if [[ "$object_voxel_size" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
    cmd+=" --voxel-size $object_voxel_size"
  else
    echo "Warning: object_voxel_size '$object_voxel_size' is not numeric; skipping." >&2
  fi
fi

echo "Running: ${cmd}"
eval "${cmd}"
