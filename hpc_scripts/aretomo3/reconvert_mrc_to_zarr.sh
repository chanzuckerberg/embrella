#!/bin/bash
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=16G
#SBATCH --time=4:00:00
#SBATCH --job-name=reconvert_zarr
#SBATCH --output=JOB%j.out
#SBATCH --error=JOB%j.err

# Reconvert existing MRC files to zarr using zarrczar, renaming old rechunked versions.
# Processes all *_Vol.mrc files in <directory>/<vol_dir>/ with up to 4 parallel workers.
#
# Usage: $0 <directory> <vol_dir>
#
# Example:
#   $0 /hpc/projects/group.czii/krios1.processing/session123 vol001

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <directory> <vol_dir>"
    exit 1
fi

directory="$1"
vol_dir="$2"
MAX_JOBS=4

ml anaconda
conda activate /hpc/projects/group.czii/krios1.processing/aretomo3/scripts/zarrczar_env

wait_for_jobs() {
    while (( $(jobs -rp | wc -l) >= MAX_JOBS )); do
        sleep 1
    done
}

convert_one() {
    local vol_path="$1"
    local zarr_path="${vol_path%.mrc}.zarr"
    local rechunked_path="${vol_path%.mrc}_rechunked.zarr"

    # Skip if already reconverted
    if [ -d "$rechunked_path" ]; then
        echo "[SKIP] Already reconverted: $vol_path"
        return
    fi

    # Rename existing zarr to _rechunked
    if [ -d "$zarr_path" ]; then
        echo "[INFO] Renaming $zarr_path -> $rechunked_path"
        mv "$zarr_path" "$rechunked_path"
    fi

    echo "[INFO] Converting $vol_path -> $zarr_path"
    if ! zarrczar convert --mrc-path "$vol_path" --zarr-path "$zarr_path"; then
        echo "[ERROR] Convert failed for $vol_path, cleaning up partial zarr"
        rm -rf "$zarr_path"
        # Restore the rechunked version if we renamed it
        if [ -d "$rechunked_path" ]; then
            mv "$rechunked_path" "$zarr_path"
        fi
        return 1
    fi
    zarrczar compute-image-stats "$zarr_path"
    zarrczar compute-filesystem-stats "$zarr_path"
    echo "[INFO] Done: $zarr_path"
}

search_dir="${directory}/${vol_dir}"
if [ ! -d "$search_dir" ]; then
    echo "[ERROR] Directory not found: $search_dir"
    exit 1
fi

count=0
for vol_path in "${search_dir}"/*_Vol.mrc; do
    [ -f "$vol_path" ] || continue
    wait_for_jobs
    convert_one "$vol_path" &
    ((count++))
done

echo "[INFO] Launched $count conversion jobs, waiting for completion..."
wait
echo "[INFO] All done."
