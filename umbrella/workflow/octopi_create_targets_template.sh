#!/bin/bash

#SBATCH --job-name=
#SBATCH --time=72:00:00
#SBATCH --partition=gpu
#SBATCH --gpus=4
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=32G