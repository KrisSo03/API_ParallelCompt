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
START_DATE="${START_DATE:-2001-01-01}"
END_DATE="${END_DATE:-2023-12-31}"
STAGING_ROOT="${STAGING_ROOT:-/data/${USER}/renewable-atlas/aws-staging}"
PUBLISH_RESULTS="${PUBLISH_RESULTS:-false}"

PUBLISH_ARGS=()
if [[ "${PUBLISH_RESULTS}" == "true" ]]; then
  PUBLISH_ARGS+=(--publish-results)
fi

python -m renewable_atlas aws-run \
  --experiment-id "${EXPERIMENT_ID}" \
  --points "${POINTS}" \
  --start-date "${START_DATE}" \
  --end-date "${END_DATE}" \
  --target-gib "${TARGET_GIB}" \
  --size-basis logical \
  --staging-root "${STAGING_ROOT}" \
  --download \
  "${PUBLISH_ARGS[@]}"
