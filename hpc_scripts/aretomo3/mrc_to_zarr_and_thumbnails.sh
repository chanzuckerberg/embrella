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
    python <<EOF
import os
import mrcfile
from mrcfile.mrcfile import MrcFile
print(mrcfile.__version__)
print(mrcfile.__file__)
import numpy as np
import io
from PIL import Image

def bin_ndarray(arr, bin_factors):
    shape = tuple(s // f for s, f in zip(arr.shape, bin_factors))
    trimmed = arr[:shape[0]*bin_factors[0], :shape[1]*bin_factors[1], :shape[2]*bin_factors[2]]
    reshaped = trimmed.reshape(shape[0], bin_factors[0], shape[1], bin_factors[1], shape[2], bin_factors[2])
    return reshaped.mean(axis=(1,3,5))

def generate_thumbnail(mrc_path, jpeg_path, bin_factors):
    try:
        with MrcFile(mrc_path, permissive=True) as mrc:
            volume = mrc.data.astype(np.float32)
        volume = np.transpose(volume, (2, 1, 0))
        binned = bin_ndarray(volume, bin_factors)
        center_slice = binned[:, :, binned.shape[2] // 2]
        norm_slice = 255 * (center_slice - np.min(center_slice)) / (np.max(center_slice) - np.min(center_slice) + 1e-8)
        img = Image.fromarray(norm_slice.astype(np.uint8))
        img.save(jpeg_path)
    except Exception as e:
        print(f"[WARN] Skipping {mrc_path}: {e}")

base = "${directory}"
base_name = "${base_name}"

vol_path = os.path.join(base, "vol003", base_name + "_Vol.mrc")
thumb_path = os.path.join(base, "thumbnails", base_name + ".jpeg")
if os.path.exists(vol_path) and not os.path.exists(thumb_path):
    os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
    generate_thumbnail(vol_path, thumb_path, (4, 4, 2))

ctf_path = os.path.join(base, base_name + "_CTF.mrc")
ctf_thumb = os.path.join(base, "ctf_thumbnails", base_name + ".jpeg")
if os.path.exists(ctf_path) and not os.path.exists(ctf_thumb):
    os.makedirs(os.path.dirname(ctf_thumb), exist_ok=True)
    generate_thumbnail(ctf_path, ctf_thumb, (4, 4, 1))
EOF

# convert mrc to zarr in background (throttled by wait_for_jobs)
for vol_dir in "vol001" "vol003"; do
    local vol_path="${directory}/${vol_dir}/${base_name}_Vol.mrc"
    if [ -f "$vol_path" ]; then
        wait_for_jobs
        echo "[mrc to zarr] Launching $vol_path"
        local zarr_path="${vol_path%.mrc}.zarr"
        (
            zarrczar convert --mrc-path "$vol_path" --zarr-path "$zarr_path"
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
