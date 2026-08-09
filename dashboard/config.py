"""Shared configuration for the Streamlit dashboard."""

from __future__ import annotations

import os
from pathlib import Path


APP_TITLE = "Atlas de Energía Renovable"
APP_SUBTITLE = "Potencial solar, eólico e híbrido de Centroamérica"
RESULTS_ENV_VAR = "ATLAS_RESULTS_DIR"


def results_root() -> Path:
    """Return the configured experiment directory without requiring a fixed machine path."""
    return Path(os.getenv(RESULTS_ENV_VAR, "results")).expanduser().resolve()


def discover_experiments(root: Path) -> list[Path]:
    """List experiment directories in newest-first order."""
    if not root.is_dir():
        return []
    return sorted(
        (path for path in root.iterdir() if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

