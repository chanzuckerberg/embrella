# Scripts Hosted on HPC

This directory contains scripts hosted on HPC utilized by Embrella.

For now, a copy is kept in the repo. We will plan to standardize them at some point.

## Directory Contents

- /aretomo3/
  - mrc_to_zarr_and_thumbnails.sh -- Contains replacement for aretomo3/scripts/reformat_thumbnail_rechunk.sh. Uses zarrczarr internal package and removes rechunking.
  - reconvert_mrc_to_zarr.sh -- Replace prior 2d rechunked zarrs with 3d
- /denoiset/
  - mrc_to_zarr.sh -- Deployed to `denoise/scripts/`. Run in the background of the denoise job; polls the flat run dir and converts each new MRC to zarr with zarrczar. Args: `<directory> <done_file> <wait_time> <max_checks>`. Exits after a final pass once the job touches `<done_file>` (predict3d finished). Expects the zarrczar env already activated.

## Custom Environments Created

```bash
ml anaconda
conda create --prefix <software_root>/zarrczar_env python="3.12.12"
conda activate <software_root>/zarrczar_env
# clone zarrczar repo https://github.com/czimaginginstitute/zarrczar
cd zarrczar_repo
pip install .
```
