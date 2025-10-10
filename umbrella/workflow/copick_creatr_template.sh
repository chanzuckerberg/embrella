#!/bin/bash

#SBATCH --job-name=denoise
#SBATCH --time=140:00:00
#SBATCH --partition=gpu
#SBATCH --gpus=1
#SBATCH --mem-per-cpu=196G

ml anaconda
conda activate /hpc/projects/group.czii/conda_environments/pyczii

session="{{ session }}"
copick_procrun="{{ copickRun }}"

tomo_type="{{ importTomoType }}"
tomo_run="{{ importTomogramRun }}"

tomo_downsamplevoxel_size="{{ downsampleTomogramVoxelSize }}"

copick_dir="/hpc/projects/group.czii/krios1.processing/copick/${session}/${copick_procrun}"

case "$tomo_type" in
  DCTF)
    tomo_path="/hpc/projects/group.czii/krios1.processing/aretomo3/${session}/${tomo_run}/*/vol001"
    ;;
  WBP)
    tomo_path="/hpc/projects/group.czii/krios1.processing/aretomo3/${session}/${tomo_run}/*/vol002"
    ;;
  Denoise)
    tomo_path="/hpc/projects/group.czii/krios1.processing/denoise/${session}/${tomo_run}"
    ;;
  *)
    # Default fallback if none match
    tomo_path="/hpc/projects/group.czii/krios1.processing/aretomo3/${session}/${tomo_run}/*/vol001"
    ;;
esac

# create config file
copick config filesystem \
    --config ${copick_dir}/config.json \
    --overlay-root ${copick_dir} \
    --proj-name ${session}_copickProcRun${session}_${tomo_type}_tomoProcRun${tomo_run} \

if [ "${tomo_type}" == "DCTF" ]; then
    copick add tomogram \
        --config ${copick_dir}/config.json \
        --tomo-type dctf \
        --run-regex ${tomo_path}'^(.*?)(?:_(?:EVN|ODD))?\.mrc$' \
        --no-create-pyramid \

