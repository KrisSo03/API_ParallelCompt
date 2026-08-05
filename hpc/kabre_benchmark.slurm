#!/usr/bin/env bash
#SBATCH --job-name=atlas-benchmark
#SBATCH --output=outputs/slurm/%x-%j.out
#SBATCH --error=outputs/slurm/%x-%j.err
#SBATCH --partition=kura
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?Envíe el trabajo desde la raíz del proyecto}"
source .venv-kabre/bin/activate

EXPERIMENT_ID="${EXPERIMENT_ID:-kabre-benchmark-${SLURM_JOB_ID}}"
POINTS="${POINTS:-50}"
REPEATS="${REPEATS:-3}"
SOURCE="${SOURCE:-fake}"
WORKERS="${WORKERS:-1,2,4,8}"

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONHASHSEED=42

# La entrada se descarga/genera una vez y se reutiliza para toda la matriz.
python -m renewable_atlas hpc-benchmark \
    --experiment-id "$EXPERIMENT_ID" \
    --source "$SOURCE" \
    --points "$POINTS" \
    --workers "$WORKERS" \
    --repeats "$REPEATS" \
    --scheduler processes
