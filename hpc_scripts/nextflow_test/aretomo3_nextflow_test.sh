#!/bin/bash -l

# Component 0: AreTomo3 GPU Processing
#SBATCH --job-name=aretomo3_26jan09a_run890_vol001
#SBATCH --partition=gpu
#SBATCH --gres=gpu:8
#SBATCH --nodes=1
#SBATCH --cpus-per-task=16
#SBATCH --mem-per-gpu=96G
#SBATCH --time=140:00:00
#SBATCH --mail-type=ALL
#SBATCH -o /hpc/projects/group.czii/krios1.processing/aretomo3/26jan09a/run890/JOB%j_aretomo3.out
#SBATCH -e /hpc/projects/group.czii/krios1.processing/aretomo3/26jan09a/run890/JOB%j_aretomo3.err

#SBATCH hetjob

# Component 1: Reformat and Metrics CPU Processing
#SBATCH --job-name=aretomo3_26jan09a_run890_vol001_reformat
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=196G
#SBATCH --time=140:00:00
#SBATCH -o /hpc/projects/group.czii/krios1.processing/aretomo3/26jan09a/run890/JOB%j_reformat.out
#SBATCH -e /hpc/projects/group.czii/krios1.processing/aretomo3/26jan09a/run890/JOB%j_reformat.err

# Context variables
export project_name="26jan09a"
export run_number="run890"
export user_id="david.dong@czbiohub.org"
export job_name="aretomo3_26jan09a_run890_vol001"
# Calculated variables
export tomo_bin_5A=3.25
export tomo_bin_10A=6.49
export slurm_component_0_gpus=8
# Schema-driven bash variables (from parameter schema)
export pix_size="1.54"
export kv=300
export cs=2.7
export tilt_axis_refine=1
export AlignZ=0
export VolZ=1600
export imod_option=1
export local_aln_1=4
export local_aln_2=4
export tilt_cor=False
export temp="0"
export return_value=False
export in_prefix="${in_mdoc_dir}/${project_name}/Position_"
export in_suffix=".mdoc"
export in_skips=""
export cmd_mode=0
export resume_processing=True
export skip_alignment=True
export serial=43000
export mc_patch="4 4"
export mc_iter=15
export mc_tol=0.1
export mc_bin=2
export eer_sampling=2
export group_frames="2 4"
export fm_ref=-1
export in_fm_motion=False
export mag_correction=""
export defect_file=""
export dark_reference=""
export rot_gain=0
export flip_gain=1
export inv_gain=False
export dark_tol=0.7
export ext_z=300
export at_bin=""
export recon_range=""
export sart_iterations="20 5"
export use_wbp=True
export flip_vol=True
export flip_int=False
export intp_cor=False
export out_xf=False
export amp_contrast=0.07
export ext_phase=""
export corr_ctf=1
# Input paths
export in_mdoc_dir="/hpc/instruments/czii.krios1/OffloadData"
export gain_fn="/hpc/instruments/czii.krios1/OffloadData/ImagesForProcessing/EF-Falcon/300kV/20251218_093959_EER_GainReference.gain"

# Output path
export out_path="/hpc/projects/group.czii/krios1.processing/aretomo3/${project_name}/${run_number}"
mkdir -p "${out_path}/vol001" "${out_path}/vol002" "${out_path}/vol003"
chmod 775 "${out_path}"

# Create temp directory if needed for thickness measurement
# (temp variable is set by schema-driven generation)
if [[ "${temp:-0}" != "0" ]] && [[ -n "${temp}" ]]; then
    mkdir -p "${temp}"
fi

# Print the collected inputs
echo "Project Name: ${project_name}"
echo "Gain Path: ${gain_fn}"
echo "Output Path: ${out_path}"
echo "Pixel Size: ${pix_size}"
echo "At binning for 5A vol: ${tomo_bin_5A}"
echo "At binning for 10A vol: ${tomo_bin_10A}"

echo "Frame dose: using MDOC ExposureDose"



# Define bash functions for heterogeneous job components
run_aretomo3_gpu() {
    set -e
    ml cuda

    # AreTomo3 command with fixed flags and schema-generated variable flags
    /hpc/projects/group.czii/krios1.processing/software/executables/AreTomo3_2.2.8_Cuda13_02-08-2026 \
        -Gain ${gain_fn} \
        -OutDir ${out_path} \
        -Gpu 0,1,2,3,4,5,6,7 \
        -PixSize 1.54 \
        -kV 300 \
        -AlignZ 0 \
        -VolZ 1600 \
        -OutImod 1 \
        -AtPatch 4 4 \
        -SplitSum 0 \
        -InPrefix ${in_mdoc_dir}/${project_name}/Position_ \
        -InSuffix .mdoc \
        -Resume 1 \
        -Serial 43000 \
        -McPatch 4 4 \
        -McBin 2 \
        -EerSampling 2 \
        -Group 2 4 \
        -FmRef -1 \
        -InFmMotion 0 \
        -FlipGain 1 \
        -ExtZ 300 \
        -AtBin 3.25 6.49 6.49 \
        -Sart 20 5 \
        -Wbp 1 \
        -FlipVol 1 \
        -IntpCor 0 \
        2>&1
}

run_reformat_cpu() {
    set -e
    ml anaconda
    conda activate /hpc/projects/group.czii/krios1.processing/aretomo3/scripts/zarrczar_env
    bash /hpc/projects/group.czii/krios1.processing/aretomo3/scripts/mrc_to_zarr_and_thumbnails.sh ${out_path} 960 180

    conda activate /hpc/projects/group.czii/krios1.processing/software/slabpick/pySlabPick
    python /hpc/projects/group.czii/krios1.processing/software/diagnostics/scripts/plot_aretomo3_metrics.py --session ${project_name} --run ${run_number}
    python /hpc/projects/group.czii/krios1.processing/software/diagnostics/scripts/summary_aretomo3_metrics.py
}

# Export functions so they're available to srun subshells
export -f run_aretomo3_gpu
export -f run_reformat_cpu

# Launch Component 0 (GPU processing) in parallel
srun --het-group=0 bash -c 'run_aretomo3_gpu' &

# Launch Component 1 (CPU processing) in parallel
srun --het-group=1 bash -c 'run_reformat_cpu' &

# Wait for both components to complete
wait

echo "AreTomo3 hetjob completed!"