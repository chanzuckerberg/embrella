#!/bin/bash

# Input paths
in_mdoc_dir="/hpc/instruments/czii.krios1/OffloadData/{{ project_name }}"
gain_dir="/hpc/instruments/czii.krios1/OffloadData/ImagesForProcessing/EF-Falcon/300kV/"
gain_fn=$(ls -t $gain_dir | head -n 1)

if [[ -z "$gain_fn" ]]; then
    echo "Gain file not found in $gain_dir"
    exit 1
fi

# Output path
out_path="/hpc/projects/group.czii/krios1.processing/aretomo3/{{ project_name }}/run{{ run_number }}"
mkdir -p "$out_path/vol001" "$out_path/vol002" "$out_path/vol003"
chmod 775 "$out_path"

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
#SBATCH --mail-user={{ user_id }}@czii.org
#SBATCH --mail-type=ALL
#SBATCH -o ${out_path}/JOB%j.out 
#SBATCH -e ${out_path}/JOB%j.err

ml cuda
/hpc/projects/group.czii/krios1.processing/software/executables/AreTomo3_2.1.10_05-08-2025 -InPrefix $in_mdoc_dir/Position_ -InSuffix .mdoc -Gain  $gain_dir $gain_fn -OutDir $out_path -EerSampling 2 -McBin 2 -McPatch 4 4 -Group 2 4 -SplitSum 1 -PixSize {{ pix_size }} -AtBin {{ tomo_bin_5A }} {{ tomo_bin_10A }} {{ tomo_bin_10A }} -AtPatch 4 4 -Wbp 1 -FlipVol 1 -VolZ 1600 -OutImod 1 -TotalDose {{ total_dose }} -FmDose {{ frame_dose }} -Resume 1 -FlipGain 1 -Serial 43000 -Gpu 0,1,2,3,4,5,6,7 2>/dev/null

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
python /hpc/projects/group.czii/krios1.processing/software/diagnostics/scripts/plot_aretomo3_metrics.py --session {{ project_name }} --run {{ run_number }}
python /hpc/projects/group.czii/krios1.processing/software/diagnostics/scripts/summary_aretomo3_metrics.py

EOF

# Make the Slurm script executable
chmod +x "$out_path/slurm_script_reformat.sh"

# Submit the job
sbatch "$out_path/slurm_script_reformat.sh"

echo "Jobs submitted!" 