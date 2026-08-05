#!/usr/bin/env bash
#SBATCH --job-name=renewable-atlas
#SBATCH --output=outputs/slurm/%x-%A_%a.out
#SBATCH --error=outputs/slurm/%x-%A_%a.err
#SBATCH --partition=kura
#SBATCH --array=0-3
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?Envíe el trabajo desde la raíz del proyecto}"
source .venv-kabre/bin/activate

WORKER_MATRIX=(1 2 4 8)
WORKERS="${WORKER_MATRIX[$SLURM_ARRAY_TASK_ID]}"
EXPERIMENT_ID="${EXPERIMENT_ID:-kabre-${SLURM_ARRAY_JOB_ID}}"
POINTS="${POINTS:-300}"
REPEATS="${REPEATS:-3}"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONHASHSEED=42

python -m renewable_atlas hpc-run \
    --experiment-id "$EXPERIMENT_ID" \
    --source fake \
    --points "$POINTS" \
    --workers "$WORKERS" \
    --repeats "$REPEATS" \
    --scheduler processes
