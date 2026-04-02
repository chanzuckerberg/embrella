#!/bin/bash
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=196G
#SBATCH --time=140:00:00

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <path> <project_name> <run_number>"
    exit 1
fi

out_path="$1"
project_name="$2"
run_number="$3"

ml anaconda
conda activate /hpc/projects/group.czii/krios1.processing/aretomo3/scripts/zarrczar_env
bash /hpc/projects/group.czii/krios1.processing/aretomo3/scripts/mrc_to_zarr_and_thumbnails.sh "${out_path}" 960 180

conda activate /hpc/projects/group.czii/krios1.processing/software/slabpick/pySlabPick
python /hpc/projects/group.czii/krios1.processing/software/diagnostics/scripts/plot_aretomo3_metrics.py --session "${project_name}" --run "${run_number}"
python /hpc/projects/group.czii/krios1.processing/software/diagnostics/scripts/summary_aretomo3_metrics.py
