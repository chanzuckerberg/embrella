#!/bin/bash

# Set variables from template parameters
project_name="{{ project_name }}"
run_number="{{ run_number }}"
pix_size="{{ pix_size }}"
total_dose="{{ total_dose }}"
frame_dose="{{ frame_dose }}"
usr_id="{{ user_id }}"
tomo_bin_5A={{ tomo_bin_5A }}
tomo_bin_10A={{ tomo_bin_10A }}

# Input paths
in_mdoc_dir="/hpc/instruments/czii.krios1/OffloadData/$project_name"
gain_dir="/hpc/instruments/czii.krios1/OffloadData/ImagesForProcessing/EF-Falcon/300kV/"
gain_fn=$(ls -t $gain_dir | head -n 1)

if [[ -z "$gain_fn" ]]; then
    echo "Gain file not found in $gain_dir"
    exit 1
fi

# Output path
out_path="/hpc/projects/group.czii/krios1.processing/aretomo3/$project_name/$run_number"
mkdir -p "$out_path/vol001" "$out_path/vol002" "$out_path/vol003"
chmod 775 "$out_path"

# Print the collected inputs
echo "Project Name: $project_name"
echo "Gain Path: $gain_dir/$gain_fn"
echo "Output Path: $out_path"
echo "Pixel Size: $pix_size"
echo "At binning for 5A vol: $tomo_bin_5A"
echo "At binning for 10A vol: $tomo_bin_10A"
echo "Total dose is: $total_dose"
echo "Frame dose is: $frame_dose"

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
/hpc/projects/group.czii/krios1.processing/software/executables/AreTomo3_2.2.2_07-11-2025 -InPrefix $in_mdoc_dir/Position_ -InSuffix .mdoc -Gain  $gain_dir$gain_fn -OutDir $out_path -EerSampling 2 -McBin 2 -McPatch 4 4 -Group 2 4 -kV 300 -SplitSum 1 -PixSize $pix_size -AtBin $tomo_bin_5A $tomo_bin_10A $tomo_bin_10A -AtPatch 4 4 -Wbp 1 -FlipVol 1 -VolZ 1600 -OutImod 1 -TotalDose $total_dose -FmDose $frame_dose -Resume 1 -FlipGain 1 -Serial 43000 -Gpu 0,1,2,3,4,5,6,7 2>/dev/null

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

ml anaconda
conda activate /hpc/projects/group.czii/krios1.processing/aretomo3/scripts/pyConvert
bash /hpc/projects/krios1.processing/aretomo3/scripts/reformat_thumbnail_rechunk.sh ${out_path} 960 180

conda activate /hpc/projects/group.czii/krios1.processing/software/slabpick/pySlabPick
python /hpc/projects/group.czii/krios1.processing/software/diagnostics/scripts/plot_aretomo3_metrics.py --session $project_name --run $run_number
python /hpc/projects/group.czii/krios1.processing/software/diagnostics/scripts/summary_aretomo3_metrics.py

EOF

# Make the Slurm script executable
chmod +x "$out_path/slurm_script_reformat.sh"

# Submit the job
sbatch "$out_path/slurm_script_reformat.sh"

echo "Jobs submitted!" 