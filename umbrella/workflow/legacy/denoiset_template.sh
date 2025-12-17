#!/bin/bash

#SBATCH --job-name=denoise
#SBATCH --time=140:00:00
#SBATCH --partition=gpu
#SBATCH --gpus=1
#SBATCH --mem-per-cpu=196G

ml anaconda
conda activate /hpc/projects/group.czii/krios1.processing/software/denoiset/pyDenoiset

session="{{ session }}"
aretomo_run="{{ aretomo_run }}"
denoise_run="{{ denoise_run }}"
model_name="{{ model_name }}"
in_dir="/hpc/projects/group.czii/krios1.processing/aretomo3/${session}/${aretomo_run}/vol001"
out_dir="/hpc/projects/group.czii/krios1.processing/denoise/${session}/${denoise_run}"
model="/hpc/projects/group.czii/krios1.processing/software/denoiset/denoiset/models/${model_name}"

predict3d --model ${model} --input ${in_dir} --output ${out_dir}{% if live_denoising %} --live --t_exit 43000 {% endif %}

julia /hpc/projects/group.czii/krios1.processing/software/php/DoPHplot.jl --dcroot /hpc/instruments/czii.krios1/OffloadData/${session}/ --apdroot /hpc/projects/group.czii/krios1.processing/aretomo3/${session}/${aretomo_run}/ --dnroot ${out_dir} --ExptName ${session} --comment "Aretomo v2.0.0, denoised"
julia /hpc/projects/group.czii/krios1.processing/software/php/IndexWebRootDir.jl

# --- Rechunk denoised volumes (5 checks, wait 10s between)
bash /hpc/projects/krios1.processing/denoise/scripts/rechunk.sh "${out_dir}" 5 10