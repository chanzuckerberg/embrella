#!/bin/bash

#SBATCH --job-name=denoise
#SBATCH --time=140:00:00
#SBATCH --partition=gpu
#SBATCH --gpus=1
#SBATCH --mem-per-cpu=196G

ml anaconda
conda activate /hpc/projects/group.czii/conda_environments/pyczii

#initialize parameters
session="{{ session }}"
copick_procrun="{{ copickRun }}"

tomo_type="{{ importTomoType }}"
tomo_run="{{ importTomogramRun }}"

tomo_downsamplevoxel_size="{{ downsampleTomogramVoxelSize }}"

copick_dir="/hpc/projects/group.czii/krios1.processing/copick/${session}/${copick_procrun}"

mkdir -p "${copick_dir}"

# --- dynamically set log paths for this job ---
JOBTAG="${session}_${copick_procrun}_${SLURM_JOB_ID:-$$}"
LOG_OUT="${copick_dir}/${JOBTAG}.out"
LOG_ERR="${copick_dir}/${JOBTAG}.err"
exec >"${LOG_OUT}" 2>"${LOG_ERR}"

# map tomogram paths
case "${tomo_type,,}" in
  dctf)
    tomo_path="/hpc/projects/group.czii/krios1.processing/aretomo3/${session}/${tomo_run}/vol001/*.mrc"
    ;;
  wbp)
    tomo_path="/hpc/projects/group.czii/krios1.processing/aretomo3/${session}/${tomo_run}/vol002/*.mrc"
    ;;
  denoise)
    tomo_path="/hpc/projects/group.czii/krios1.processing/denoise/${session}/${tomo_run}/*.mrc"
    ;;
  *)
    # Default fallback if none match
    tomo_path="/hpc/projects/group.czii/krios1.processing/aretomo3/${session}/${tomo_run}/vol001/*.mrc"
    ;;
esac

# create config file
copick config filesystem \
    --config ${copick_dir}/config.json \
    --overlay-root ${copick_dir} \
    --proj-name ${session}_copickProcRun${session}_${tomo_type}_tomoProcRun${tomo_run} \
    --proj-description "Embrella created copick processing for msi session ${session} tomogram type ${tomo_type} and tomogram processing run ${tomo_run}"

# add tomograms with path specific to tomo type, excluding EVN and ODD runs.
copick add tomogram "${tomo_path}" \
  --config "${copick_dir}/config.json" \
  --tomo-type "${tomo_type,,}" \
  --run-regex '^(Position_[0-9]+(?:_[0-9]+)*)_Vol$'
  
# downsample tomograms, first check the smallest voxel size avaliable

# ------------------------------------------------------------------
# Get smallest common voxel size for given tomo_type using Python
# ------------------------------------------------------------------
voxel_size=$(python3 - <<PY
import copick, math
from copick.ops.get import from_file, get_tomograms, get_runs

def extract_voxsize(tomo):
    vs = getattr(tomo, "voxel_spacing", None)
    if vs and hasattr(vs, "voxel_size"):
        return float(vs.voxel_size)
    for attr in ("voxel_size", "spacing", "voxel"):
        if hasattr(tomo, attr):
            try:
                return float(getattr(tomo, attr))
            except (TypeError, ValueError):
                pass
    meta = getattr(tomo, "meta", None)
    if isinstance(meta, dict):
        for k in ("voxel_size", "spacing", "voxel"):
            try:
                return float(meta.get(k))
            except (TypeError, ValueError):
                pass
    return None

def smallest_common_vox_for_type(config_path: str, tomo_type: str):
    root = from_file(config_path)
    per_run_sets = []
    for run in get_runs(root):
        tomos = get_tomograms(root, runs=[run], tomo_type=tomo_type)
        sizes = {extract_voxsize(t) for t in tomos}
        sizes.discard(None)
        if not sizes:
            return None
        per_run_sets.append(sizes)
    common = set.intersection(*per_run_sets) if per_run_sets else set()
    return min(common) if common else None

config_path = "${copick_dir}/config.json"
tomo_type = "${tomo_type}".lower()

v = smallest_common_vox_for_type(config_path, tomo_type)
if v is not None:
    print(v)
PY
)

if [[ ${tomo_downsamplevoxel_size} =~ ^[0-9]+([.][0-9]+)?$ ]] && [[ ${voxel_size} =~ ^[0-9]+([.][0-9]+)?$ ]]; then
  copick process downsample \
    --config "${copick_dir}/config.json" \
    --tomo-alg "${tomo_type,,}" \
    --voxel-size "${voxel_size}" \
    --target-resolution "${tomo_downsamplevoxel_size}"
else
  echo "Skip downsample: voxel_size='${voxel_size}', target='${tomo_downsamplevoxel_size}'"
fi


