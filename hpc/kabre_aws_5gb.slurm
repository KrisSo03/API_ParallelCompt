#!/usr/bin/env bash
#SBATCH --job-name=atlas-aws-5gb
#SBATCH --output=outputs/slurm/atlas-aws-5gb-%j.out
#SBATCH --error=outputs/slurm/atlas-aws-5gb-%j.err
#SBATCH --time=1-00:00:00
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --partition=kura

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?Envíe el trabajo desde la raíz del proyecto}"
module purge
module load mamba/python-3.12.11
source .venv-kabre/bin/activate

EXPERIMENT_ID="${EXPERIMENT_ID:-nasa-aws-5gb-${SLURM_JOB_ID}}"
POINTS="${POINTS:-300}"
TARGET_GIB="${TARGET_GIB:-5}"
SIZE_BASIS="${SIZE_BASIS:-logical}"
START_DATE="${START_DATE:-2016-01-01}"
# Fecha común más reciente verificada para syn1deg y MERRA-2 hourly LST.
END_DATE="${END_DATE:-2026-05-30}"
STAGING_ROOT="${STAGING_ROOT:-/data/${USER}/renewable-atlas/aws-staging}"
WORKERS="${WORKERS:-1,2,4,8}"
REPEATS="${REPEATS:-1}"
RESULTS_DIR="${RESULTS_DIR:-${SLURM_SUBMIT_DIR}/results}"
MAIN_BASELINE="${MAIN_BASELINE:-false}"
DOWNLOAD="${DOWNLOAD:-true}"

BASELINE_ARGS=()
if [[ "${MAIN_BASELINE}" == "true" ]]; then
  BASELINE_ARGS+=(--main-baseline)
fi
DOWNLOAD_ARGS=()
if [[ "${DOWNLOAD}" == "true" ]]; then
  DOWNLOAD_ARGS+=(--download)
fi

python -m renewable_atlas aws-run \
  --experiment-id "${EXPERIMENT_ID}" \
  --points "${POINTS}" \
  --start-date "${START_DATE}" \
  --end-date "${END_DATE}" \
  --target-gib "${TARGET_GIB}" \
  --size-basis "${SIZE_BASIS}" \
  --staging-root "${STAGING_ROOT}" \
  --workers "${WORKERS}" \
  --repeats "${REPEATS}" \
  --scheduler threads \
  --results-dir "${RESULTS_DIR}" \
  "${DOWNLOAD_ARGS[@]}" \
  "${BASELINE_ARGS[@]}"
