if [ -z "$1" ]; then
    echo "Usage: $0 {session}"
    exit 1
fi

session="$1"

# Paths
raw_data_path="/hpc/instruments/czii.krios1/OffloadData/{{ session }}/Position_*.mdoc"
aretomo_base="/hpc/projects/krios1.processing/aretomo3/{{ session }}"
denoise_base="/hpc/projects/krios1.processing/denoise/{{ session }}"

# 1) Count raw data .mdoc files
raw_count=$(ls $raw_data_path 2>/dev/null | wc -l)
echo "1) Number of raw data .mdoc files: $raw_count"


# 2) Count alignment files for aretomo3, print available run00X
echo "2) Alignment files in aretomo3:"
for run in $(ls -d $aretomo_base/run00* 2>/dev/null | sort); do
    run_name=$(basename "$run")
    count=$(ls "$run"/Position_*.aln 2>/dev/null | wc -l)
    echo "   $run_name: $count"
done

# 3) Count SART volumes in aretomo3, print available run00X
echo "3) SART volumes in aretomo3:"
for run in $(ls -d $aretomo_base/run00* 2>/dev/null | sort); do
    run_name=$(basename "$run")
    count=$(ls "$run"/vol003/Position_*_Vol.mrc 2>/dev/null | wc -l)
    echo "   $run_name: $count"
done

# 4) Count denoise volumes, print available run00X
echo "4) Denoise volumes in denoise:"
for run in $(ls -d $denoise_base/run00* 2>/dev/null | sort); do
    run_name=$(basename "$run")
    count=$(ls "$run"/Position_*_Vol.mrc 2>/dev/null | wc -l)
    echo "   $run_name: $count"
done