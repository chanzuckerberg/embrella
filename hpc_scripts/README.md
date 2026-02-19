# Scripts Hosted on HPC

This directory contains scripts hosted on HPC utilized by Embrella.

For now, a copy is kept in the repo. We will plan to standardize them at some point.

## Directory Contents

- /aretomo3/
  - mrc_to_zarr_and_thumbnails.sh -- Contains replacement for aretomo3/scripts/reformat_thumbnail_rechunk.sh. Uses zarrczarr internal package and removes rechunking.
  - reconvert_mrc_to_zarr.sh -- Replace prior 2d rechunked zarrs with 3d

## Custom Environments Created

```bash
ml anaconda
conda create --prefix zarrczar_env python="3.12.12"
conda activate zarrczar_env
# clone zarrczar repo https://github.com/czimaginginstitute/zarrczar
cd zarrczar_repo
pip install .
```
