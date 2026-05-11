#!/bin/bash

# --- Check and parse command-line arguments ---
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <directory> <num_checks> <wait_time>"
    exit 1
fi

directory="$1"
num_checks="$2"
wait_time="$3"

# Config
MAX_CONVERSION_JOBS=8

# Setup logging
mkdir -p "$directory"
chmod g+srw "$directory"
timestamp=$(date +%Y%m%d_%H%M%S)
exec > >(tee -a "${directory}/JOB${timestamp}.out") 2> >(tee -a "${directory}/JOB${timestamp}.err" >&2)

# Activate environment
ml anaconda
conda activate /hpc/projects/group.czii/krios1.processing/aretomo3/scripts/zarrczar_env

mdoc_file="${directory}/MdocDone.txt"
processed_files=()

# Ensure folders exist
mkdir -p "${directory}/vol001" "${directory}/vol002" "${directory}/vol003" "${directory}/thumbnails" "${directory}/ctf_thumbnails"

# --- Function: limit parallel background jobs ---
wait_for_jobs() {
    while (( $(jobs -rp | wc -l) >= MAX_CONVERSION_JOBS )); do
        sleep 1
    done
}

# --- Function: move, thumbnail, mrc to zarr, contrast limits (parallel) ---
process_file() {
    local base_name="$1"
    echo "[INFO] Processing $base_name"

    # Move
    mv "${directory}/${base_name}_EVN_Vol.mrc" "${directory}/vol001/" 2>/dev/null
    mv "${directory}/${base_name}_ODD_Vol.mrc" "${directory}/vol001/" 2>/dev/null
    mv "${directory}/${base_name}_Vol.mrc" "${directory}/vol001/" 2>/dev/null
    mv "${directory}/${base_name}_2ND_Vol.mrc" "${directory}/vol002/${base_name}_Vol.mrc" 2>/dev/null
    mv "${directory}/${base_name}_3RD_Vol.mrc" "${directory}/vol003/${base_name}_Vol.mrc" 2>/dev/null

    # Thumbnails
    local vol_path="${directory}/vol003/${base_name}_Vol.mrc"
    local thumb_path="${directory}/thumbnails/${base_name}.jpeg"
    if [ -f "$vol_path" ] && [ ! -f "$thumb_path" ]; then
        zarrczar generate-thumbnail --mrc-path "$vol_path" --jpeg-path "$thumb_path" --bin "4,4,2"
    fi

    local ctf_path="${directory}/${base_name}_CTF.mrc"
    local ctf_thumb="${directory}/ctf_thumbnails/${base_name}.jpeg"
    if [ -f "$ctf_path" ] && [ ! -f "$ctf_thumb" ]; then
        zarrczar generate-thumbnail --mrc-path "$ctf_path" --jpeg-path "$ctf_thumb" --bin "4,4,1"
    fi

# convert mrc to zarr in background (throttled by wait_for_jobs)
for vol_dir in "vol001" "vol003"; do
    local vol_path="${directory}/${vol_dir}/${base_name}_Vol.mrc"
    local zarr_path="${vol_path%.mrc}.zarr"
    if [ -f "$vol_path" ] && [ ! -d "$zarr_path" ]; then
        wait_for_jobs
        echo "[mrc to zarr] Launching $vol_path"
        (
            zarrczar convert --mrc-path "$vol_path" --zarr-path "$zarr_path" --chunk-size 128
            zarrczar compute-image-stats "$zarr_path"
            zarrczar compute-filesystem-stats "$zarr_path"
        ) &
    fi
done
}

# --- Main loop ---
for ((i = 0; i < num_checks; i++)); do
    echo "[INFO] Loop $((i+1)) of $num_checks at $(date)"

    if [ -f "$mdoc_file" ]; then
        while IFS= read -r line; do
            base_name=$(basename "$line" .mdoc)
            if [[ ! " ${processed_files[@]} " =~ " ${base_name} " ]]; then
                process_file "$base_name"
                processed_files+=("$base_name")
            fi
        done < "$mdoc_file"
    fi

    if [[ $i -lt $((num_checks - 1)) ]]; then
        sleep "$wait_time"
    fi
done

# --- Wait for remaining background jobs to finish ---
echo "[INFO] Waiting for all background jobs to finish..."
wait
echo "[INFO] All done at $(date)"
