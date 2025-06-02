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
gain_fn=$(ls -t $gain_dir | head -n 1)
if [[ -z "$gain_fn" ]]; then
    echo "Gain file not found in $gain_dir"
    exit 1
fi
echo "Path to gain is: $gain_dir$gain_fn"

# Prompt user for run number
echo "Enter the run number (for example: 001):"
read run_number
if [[ -z "$run_number" ]]; then
    echo "Run number cannot be empty"
    exit 1
fi
echo "Run number is: $run_number"

# echo "Will you use this run for DenoisET training? Yes or anything else for no"
# read split_option
# # Check if the input is 'yes' (case insensitive)
# if [[ "${split_option,,}" == "yes" ]]; then
#     return_value=1
# else
#     return_value=0
# fi
# echo "EVN & ODD split option is: $split_option"

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

# Prompt user for total dose
echo "Enter the calibrated total dose in e-/A^2:"
read total_dose
if [[ -z "$total_dose" ]]; then
    echo "total_dose cannot be empty"
    exit 1
fi

tomo_bin_5A=$(echo "scale=2; 5/$pix_size" | bc)
tomo_bin_10A=$(echo "scale=2; 10/$pix_size" | bc)

echo "Enter the number of frame_dose (or leave empty to skip):"
read fm_dose

# If empty, assign 'none'
if [[ -z "$fm_dose" ]]; then
    fm_dose="none"
fi

# # Prompt user for wait time between checks (in seconds)
# echo "Enter the wait time between checks (in seconds, e.g., 180):"
# read wait_time
# if [[ -z "$wait_time" ]]; then
#     echo "Wait time cannot be empty"
#     exit 1
# fi

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
/hpc/projects/group.czii/krios1.processing/software/executables/AreTomo3_2.1.10_05-08-2025 -InPrefix $in_mdoc_dir/Position_ -InSuffix .mdoc -Gain  $gain_dir $gain_fn -OutDir $out_path -EerSampling 2 -McBin 2 -McPatch 4 4 -Group 2 4 -SplitSum 1 -PixSize $pix_size -AtBin $tomo_bin_5A $tomo_bin_10A $tomo_bin_10A -AtPatch 4 4 -Wbp 1 -FlipVol 1 -VolZ 1600 -OutImod 1 -TotalDose $total_dose -FmDose $fm_dose -Resume 1 -FlipGain 1 -Serial 43000 -Gpu 0,1,2,3,4,5,6,7 2>/dev/null

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


bash /hpc/projects/group.czii/krios1.processing/aretomo3/scripts/reformat_vols.sh ./ 960 180

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
                                                          