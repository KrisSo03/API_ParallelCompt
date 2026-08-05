#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-$PWD}"
cd "$PROJECT_DIR"

command -v python3 >/dev/null || {
    echo "Python 3 no está disponible. Cargue primero un módulo de Python." >&2
    exit 1
}

python3 -m venv .venv-kabre
source .venv-kabre/bin/activate
python -m pip install --upgrade pip
python -m pip install --requirement requirements-kabre.txt
python -m pip install --no-deps --editable .
python -m pip check
python --version
