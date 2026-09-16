#!/bin/bash

# Convert denoised MRC volumes to zarr as they appear, using zarrczar.
#
# Runs in the background of the denoise job while predict3d writes to <directory>.
# Each pass converts every *.mrc that has no sibling .zarr yet. The loop ends after
# one final pass once <done_file> exists (touched when predict3d exits), or after
# <max_checks> passes as a safety net.
#
# Usage: $0 <directory> <done_file> <wait_time> <max_checks>
#
# Example:
#   $0 /hpc/.../denoise/24nov10/run001 /hpc/.../denoise/24nov10/run001/denoise_complete.txt 180 960

if [ "$#" -ne 4 ]; then
    echo "Usage: $0 <directory> <done_file> <wait_time> <max_checks>"
    exit 1
fi

directory="$1"
done_file="$2"
wait_time="$3"
max_checks="$4"

CHUNK_SIZE=128
MAX_JOBS="${SLURM_CPUS_PER_TASK:-2}"

launched_files=()

wait_for_jobs() {
    while (( $(jobs -rp | wc -l) >= MAX_JOBS )); do
        sleep 1
    done
}

# Each MRC is attempted once. On failure the partial zarr is removed and the file is skipped.
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

# One sweep of the directory: launch a conversion per MRC not yet converted or in flight.
convert_pass() {
    for mrc_path in "${directory}"/*.mrc; do
        [ -f "$mrc_path" ] || continue
        [ -d "${mrc_path%.mrc}.zarr" ] && continue
        [[ " ${launched_files[*]} " == *" ${mrc_path} "* ]] && continue

        wait_for_jobs
        convert_one "$mrc_path" &
        launched_files+=("$mrc_path")
    done
}

mkdir -p "$directory"

for ((i = 1; i <= max_checks; i++)); do
    echo "[INFO] Pass $i of $max_checks at $(date)"
    convert_pass

    if [ -f "$done_file" ]; then
        echo "[INFO] Found $done_file, final pass complete"
        break
    fi

    sleep "$wait_time"
done

echo "[INFO] Waiting for ${#launched_files[@]} conversion jobs to finish..."
wait

# Consume the marker so a rerun in this directory polls again instead of exiting at once.
rm -f "$done_file"
echo "[INFO] All done at $(date)"
