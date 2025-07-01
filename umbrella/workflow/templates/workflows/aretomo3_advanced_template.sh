#!/bin/bash

# Prompt user for project name
echo "Enter project name (just the folder name where .eers are):"
read project_name
if [[ -z "$project_name" ]]; then
    echo "Project name cannot be empty"
    exit 1
fi
in_mdoc_dir="/hpc/instruments/czii.krios1/OffloadData/$project_name"
echo "Path to .eers is: $in_mdoc_dir"

# Gain path
gain_dir="/hpc/instruments/czii.krios1/OffloadData/ImagesForProcessing/EF-Falcon/300kV/"
# Ask the user whether they want to use an old gain reference
read -p "Do you want to use an old gain reference? (yes/no): " use_old_gain

# If they choose yes, prompt for the file name
if [[ "$use_old_gain" == "yes" ]]; then
    read -p "Please enter the gain file name, for example 20241023_110835_EER_GainReference.gain: " gain_fn
else
    # If they don't want to use an old reference, get the latest gain file
    gain_fn=$(ls -t $gain_dir | head -n 1)
fi

# Check if gain_fn is empty (no file found)
if [[ -z "$gain_fn" ]]; then
    echo "Gain file not found in $gain_dir"
    exit 1
fi

# Display the path to the selected gain file
echo "Path to gain is: $gain_dir$gain_fn"


# Prompt user for run number
echo "Enter the run number (for example: 001):"
read run_number
if [[ -z "$run_number" ]]; then
    echo "Run number cannot be empty"
    exit 1
fi
echo "Run number is: $run_number"

echo "Will you use this run for DenoisET training (yes|no): "
read split_option
# Check if the input is 'yes' (case insensitive)
if [[ "${split_option,,}" == "yes" ]]; then
    return_value=1
else
    return_value=0
fi
echo "Will you use this run for DenoisET training $split_option"

echo "EVN & ODD split option is: $split_option"

# Output path
out_path="/hpc/projects/group.czii/krios1.processing/aretomo3/$project_name/run$run_number"
mkdir -p "$out_path/vol001" "$out_path/vol002" "$out_path/vol003"
chmod 775 "$out_path"

# Prompt user for pixel size
echo "Enter the pixel size (A):"
read pix_size
if [[ -z "$pix_size" ]]; then
    echo "Pixel size cannot be empty"
    exit 1
fi
echo "Pixel size is: $pix_size"

# Ask the user if they want to use advanced parameters
read -p "Do you want to use advanced parameters? (yes/no): " use_advanced
echo "Advanced parameters is: $use_advanced"
# If the user chooses no, set default values
if [[ "${use_advanced,,}" == "no" ]]; then
    tilt_axis=0          # Set tilt_axis to an empty string
    tilt_axis_refine=1   # Set tilt_axis_refine to an empty string
    AlignZ=""              # Set AlignZ to an empty string
    VolZ=1600
    imod_option=1
    local_aln_1=4
    local_aln_2=4
    tilt_cor=0
    temp=0

else
    # If the user chooses yes, ask for each parameter
    read -p "Enter the tilt axis initial value (default is for Aretomo3 to determine): " tilt_axis
    tilt_axis="${tilt_axis:-0}"  # Default to a single space if no value is entered
read -p "Do you want Aretomo3 to refine tilt axis (yes|no): " tilt_axis_refine_answer
    if [[ "${tilt_axis_refine_answer,,}" == "yes" ]]; then
        tilt_axis_refine=1
    else
        tilt_axis_refine=-1
    fi

    read -p "Enter the AlignZ (default is for Aretomo3 to determine): " AlignZ
    AlignZ="${AlignZ:- }"  # Default to "" if the user doesn't provide a value

    read -p "Enter the VolZ (default is 1600, unit is raw pixel): " VolZ
    VolZ="${VolZ:-1600}"  # Default to 1600 if the user doesn't provide a value


    read -p "Do you want aligned tilt series in _Imod folder (yes|no): " imod_option_answer
    if [[ "${imod_option_answer,,}" == "yes" ]]; then
        imod_option=3
    else
        imod_option=1
    fi

    read -p "Do you want to measure local shifts (yes|no): " local_aln_answer
    if [[ "${local_aln_answer,,}" == "yes" ]]; then
        local_aln_1=4
        local_aln_2=4
    else
        local_aln_1=0
        local_aln_2=0
    fi

    read -p "Do you want to generate tilt offset corrected volumes (yes|no): " tiltcorr_answer
    if [[ "${tiltcorr_answer,,}" == "yes" ]]; then
        tilt_cor=1
    else
        tilt_cor=0
    fi

    read -p "Do you want to save intermediate thickness measure result (yes|no): " temp_answer
    if [[ "${temp_answer,,}" == "yes" ]]; then
        mkdir -p "$out_path/temp_thickness_measure_result"
        temp="$out_path/temp_thickness_measure_result"
    else
        temp=0
    fi

    # Display the values that were set
    echo "Tilt Axis: $tilt_axis"
    echo "AlignZ: $AlignZ"
    echo "VolZ: $VolZ"
    echo "Save aligned tiltseries: $imod_option_answer"
    echo "Local alighment: $local_aln_answer"
    echo "Tilt offset corrected volume: $tiltcorr_answer"
    echo "Save intermediate thickness results: $temp_answer"

fi
# Prompt user for total dose
echo "Enter the calibrated total dose in e-/A^2:"
read total_dose
if [[ -z "$total_dose" ]]; then
    echo "total_dose cannot be empty"
    exit 1
fi



if [[ -z "$pix_size" || ! "$pix_size" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
    echo "Error: pix_size must be a positive number."
    exit 1
fi

tomo_bin_5A=$(echo "scale=2; 5/$pix_size" | bc)
tomo_bin_10A=$(echo "scale=2; 10/$pix_size" | bc)

# # Prompt user for number of checks
# echo "Enter the estimated number of tilt series (e.g., 300; please be generous!):"
# read num_checks
# if [[ -z "$num_checks" ]]; then
#     echo "The estimated number of tilt series of checks cannot be empty"
#     exit 1
# fi
echo "Enter the number of frame_dose (or leave empty to skip):"
read fm_dose

# If empty, assign 'none'
if [[ -z "$fm_dose" ]]; then
    fm_dose="none"
fi

echo "Enter your email ID (e.g. yue.yu) to get email notification of this job:"
read usr_id
if [[ -z "$usr_id" ]]; then
    echo "Email ID cannot be empty"
    exit 1
fi

# Print the collected inputs
echo "Project Name: $project_name"
echo "Gain Path: $gain_dir/$gain_fn"
echo "Output Path: $out_path"
echo "DenoisET training option is: $split_option"
echo "Pixel Size: $pix_size"
echo "At binning for 5A vol: $tomo_bin_5A"
echo "At binning for 10A vol: $tomo_bin_10A"
echo "Estimated number of tilt series: $num_checks"
echo "Total dose is: $total_dose"
echo "Frame dose is: $fm_dose"

# echo "Wait time between checks: $wait_time seconds"

# Slurm script #1
cat > "$out_path/slurm_script_run_AT.sh" << EOF
#!/bin/bash -l

#SBATCH --job-name=aretomo
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
/hpc/projects/group.czii/krios1.processing/software/executables/AreTomo3_2.2.0_05-23-2025 -InPrefix $in_mdoc_dir/Position_ -InSuffix .mdoc -Gain $gain_dir$gain_fn -OutDir $out_path -EerSampling 2 -McBin 2 -McPatch 4 4 -Group 2 4 -PixSize $pix_size -AtBin $tomo_bin_5A $tomo_bin_10A $tomo_bin_10A -AtPatch $local_aln_1 $local_aln_2 -Wbp 1 -FlipVol 1 -AlignZ $AlignZ -VolZ $VolZ -OutImod $imod_option -SplitSum $return_value -TiltCor $tilt_cor -TotalDose $total_dose -FmDose $fm_dose -TiltAxis $tilt_axis $tilt_axis_refine -TmpDir $temp -Resume 1 -FlipGain 1 -Serial 43000 -Gpu 0,1,2,3,4,5,6,7 2>/dev/null

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
conda activate /hpc/projects/group.czii/krios1.processing/software/slabpick/pySlabPick
python /hpc/projects/group.czii/krios1.processing/software/diagnostics/scripts/plot_aretomo3_metrics.py --session $project_name --run $run_number
python /hpc/projects/group.czii/krios1.processing/software/diagnostics/scripts/summary_aretomo3_metrics.py

EOF

# Make the Slurm script executable
chmod +x "$out_path/slurm_script_reformat.sh"

# Submit the job
sbatch "$out_path/slurm_script_reformat.sh"

echo "Jobs submitted!"
