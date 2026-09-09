#!/bin/bash
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=16G
#SBATCH --time=4:00:00
#SBATCH --job-name=denoise_zarr
#SBATCH --output=JOB%j.out
#SBATCH --error=JOB%j.err

# Convert denoised MRC volumes to zarr using zarrczar.
#
# Usage: $0 <directory>
#
# Example:
#   $0 /hpc/projects/group.czii/krios1.processing/denoise/session123/denoise_run

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

directory="$1"
MAX_JOBS=4
CHUNK_SIZE=128

ml anaconda
conda activate /hpc/projects/group.czii/krios1.processing/aretomo3/scripts/zarrczar_env

wait_for_jobs() {
    while (( $(jobs -rp | wc -l) >= MAX_JOBS )); do
        sleep 1
    done
}

convert_one() {
    local mrc_path="$1"
    local zarr_path="${mrc_path%.mrc}.zarr"

    echo "[INFO] Converting $mrc_path -> $zarr_path"
    if ! zarrczar convert --mrc-path "$mrc_path" --zarr-path "$zarr_path" --chunk-size "$CHUNK_SIZE"; then
        echo "[ERROR] Convert failed for $mrc_path, cleaning up partial zarr"
        rm -rf "$zarr_path"
        return 1
    fi
    zarrczar compute-image-stats "$zarr_path"
    zarrczar compute-filesystem-stats "$zarr_path"
    echo "[INFO] Done: $zarr_path"
}

if [ ! -d "$directory" ]; then
    echo "[ERROR] Directory not found: $directory"
    exit 1
fi

launched=0
skipped=0
for mrc_path in "${directory}"/*.mrc; do
    [ -f "$mrc_path" ] || continue

    if [ -d "${mrc_path%.mrc}.zarr" ]; then
        echo "[SKIP] Zarr exists: $mrc_path"
        ((skipped++))
        continue
    fi

    wait_for_jobs
    convert_one "$mrc_path" &
    ((launched++))
done

echo "[INFO] Launched $launched conversion jobs, skipped $skipped, waiting for completion..."
wait
echo "[INFO] All done."
