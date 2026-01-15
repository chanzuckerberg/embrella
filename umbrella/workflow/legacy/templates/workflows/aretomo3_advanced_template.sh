#!/bin/bash

# Set variables from template parameters
project_name="{{ project_name }}"
use_old_gain="{{ use_old_gain }}"
run_number="{{ run_number }}"
pix_size="{{ pixel_size }}"
total_dose="{{ dose_number }}"
fm_dose="{{ frame_dose }}"
usr_id="{{ user_id }}"
tomo_bin_5A={{ tomo_bin_5A }}
tomo_bin_10A={{ tomo_bin_10A }}

# Set gain file name based on use_old_gain
gain_dir="/hpc/instruments/czii.krios1/OffloadData/ImagesForProcessing/EF-Falcon/300kV/"
if [[ "$use_old_gain" == "yes" ]]; then
    gain_fn="{{ gain_file_name }}"
else
    # Get the latest gain file
    gain_fn=$(ls -t $gain_dir | head -n 1)
fi

# Check if gain_fn is empty (no file found)
if [[ -z "$gain_fn" ]]; then
    echo "Gain file not found in $gain_dir"
    exit 1
fi

# Set denoise training option
denoise_training="{{ denoise_training }}"
if [[ "${denoise_training,,}" == "yes" ]]; then
    return_value=1
else
    return_value=0
fi

# Set advanced parameters
use_advanced_params="{{ use_advanced_params }}"
if [[ "${use_advanced_params,,}" == "no" ]]; then
    tilt_axis=0
    tilt_axis_refine=1
    AlignZ=""
    VolZ=1600
    imod_option=1
    local_aln_1=4
    local_aln_2=4
    tilt_cor=0
    temp=0
else
    # Advanced parameters from template
    tilt_axis="{{ tilt_axis }}"
    tilt_axis_refine_answer="{{ tilt_axis_refine }}"
    if [[ "${tilt_axis_refine_answer,,}" == "yes" ]]; then
        tilt_axis_refine=1
    else
        tilt_axis_refine=-1
    fi

    AlignZ="{{ align_z }}"
    VolZ="{{ vol_z }}"
    
    imod_option_answer="{{ imod_option }}"
    if [[ "${imod_option_answer,,}" == "yes" ]]; then
        imod_option=3
    else
        imod_option=1
    fi

    local_aln_answer="{{ local_shift }}"
    if [[ "${local_aln_answer,,}" == "yes" ]]; then
        local_aln_1=4
        local_aln_2=4
    else
        local_aln_1=0
        local_aln_2=0
    fi

    tiltcorr_answer="{{ tilt_offset }}"
    if [[ "${tiltcorr_answer,,}" == "yes" ]]; then
        tilt_cor=1
    else
        tilt_cor=0
    fi

    temp_answer="{{ thickness_mesaure }}"
    if [[ "${temp_answer,,}" == "yes" ]]; then
        temp="$out_path/temp_thickness_measure_result"
    else
        temp=0
    fi
fi

# Validate pixel size
if [[ -z "$pix_size" || ! "$pix_size" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
    echo "Error: pix_size must be a positive number."
    exit 1
fi

# Set up output path
in_mdoc_dir="/hpc/instruments/czii.krios1/OffloadData/$project_name"
out_path="/hpc/projects/group.czii/krios1.processing/aretomo3/$project_name/$run_number"
mkdir -p "$out_path/vol001" "$out_path/vol002" "$out_path/vol003"
chmod 775 "$out_path"

# Create temp directory if needed
if [[ "$temp" != "0" ]]; then
    mkdir -p "$temp"
fi

# Print the collected inputs
echo "Project Name: $project_name"
echo "Gain Path: $gain_dir/$gain_fn"
echo "Output Path: $out_path"
echo "DenoisET training option is: $denoise_training"
echo "Pixel Size: $pix_size"
echo "At binning for 5A vol: $tomo_bin_5A"
echo "At binning for 10A vol: $tomo_bin_10A"
echo "Total dose is: $total_dose"
echo "Frame dose is: $fm_dose"

# Slurm script #1
cat > "$out_path/slurm_script_run_AT.sh" << EOF
#!/bin/bash -l

#SBATCH --job-name={{ job_name }}
#SBATCH --gpus=8
#SBATCH --partition=gpu
#SBATCH --cpus-per-task=16
#SBATCH -N 1
#SBATCH --mem-per-gpu=96G 
#SBATCH --time=140:00:00
#SBATCH --mail-user=$usr_id@czii.org
#SBATCH --mail-type=ALL
#SBATCH -o ${out_path}/JOB%j.out 
#SBATCH -e ${out_path}/JOB%j.err

ml cuda
/hpc/projects/group.czii/krios1.processing/software/executables/AreTomo3_2.2.2_07-11-2025 -InPrefix $in_mdoc_dir/Position_ -InSuffix .mdoc -Gain $gain_dir$gain_fn -OutDir $out_path -EerSampling 2 -kV 300 -McBin 2 -McPatch 4 4 -Group 2 4 -PixSize $pix_size -AtBin $tomo_bin_5A $tomo_bin_10A $tomo_bin_10A -AtPatch $local_aln_1 $local_aln_2 -Wbp 1 -FlipVol 1 -AlignZ $AlignZ -VolZ $VolZ -OutImod $imod_option -SplitSum $return_value -TiltCor $tilt_cor -TotalDose $total_dose -FmDose $fm_dose -TiltAxis $tilt_axis $tilt_axis_refine -TmpDir $temp -Resume 1 -FlipGain 1 -Serial 43000 -Gpu 0,1,2,3,4,5,6,7 2>/dev/null

# echo CUDA_VISIBLE_DEVICES: $CUDA_VISIBLE_DEVICES
# env | grep -i slurm | sort
EOF

# Make the Slurm script executable
chmod +x "$out_path/slurm_script_run_AT.sh"

# Submit the job
sbatch "$out_path/slurm_script_run_AT.sh"

# Slurm script #2
cat > "$out_path/slurm_script_reformat.sh" << EOF
#!/bin/bash -l

#SBATCH --job-name=reformat_AT
#SBATCH --partition=cpu
#SBATCH --mem-per-cpu=196G
#SBATCH --time=140:00:00
#SBATCH -o ${out_path}/JOB%j.out 
#SBATCH -e ${out_path}/JOB%j.err

bash /hpc/projects/group.czii/krios1.processing/aretomo3/scripts/reformat_vols.sh 960 180

ml anaconda
conda activate /hpc/projects/group.czii/krios1.processing/aretomo3/scripts/pyConvert
bash /hpc/projects/krios1.processing/aretomo3/scripts/reformat_thumbnail_rechunk.sh ${out_path} 960 180

ml anaconda
conda activate /hpc/projects/group.czii/krios1.processing/software/slabpick/pySlabPick
python /hpc/projects/group.czii/krios1.processing/software/diagnostics/scripts/plot_aretomo3_metrics.py --session $project_name --run $run_number
python /hpc/projects/group.czii/krios1.processing/software/diagnostics/scripts/summary_aretomo3_metrics.py

EOF

# Make the Slurm script executable
chmod +x "$out_path/slurm_script_reformat.sh"

# Submit the job
sbatch "$out_path/slurm_script_reformat.sh"

echo "Jobs submitted!"
