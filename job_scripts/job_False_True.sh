#!/bin/bash
#SBATCH --job-name=analyze_gaze_False_True
#SBATCH --output=job_scripts/output_False_True.txt
#SBATCH --error=job_scripts/error_False_True.txt
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem-per-cpu=16G
#SBATCH --time=2:00:00
#SBATCH --partition=psych_day
#SBATCH --mail-type=FAIL

module load miniconda
conda activate nn_gpu
export map_roi_coord_to_eyelink_space=False
export map_gaze_pos_coord_to_eyelink_space=True

python analyze_gaze_signals_cluster.py
