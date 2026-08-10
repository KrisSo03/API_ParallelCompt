"""Shared configuration for the Streamlit dashboard."""

from __future__ import annotations

import os
from pathlib import Path


APP_TITLE = "Atlas de Energía Renovable"
APP_SUBTITLE = "Potencial solar, eólico e híbrido de Centroamérica"
RESULTS_ENV_VAR = "ATLAS_RESULTS_DIR"

METRICS = {
    "hybrid_score": {
        "label": "Potencial híbrido",
        "short_label": "Híbrido",
        "color": "#7057A6",
    },
    "solar_score": {
        "label": "Potencial solar",
        "short_label": "Solar",
        "color": "#F0A23A",
    },
    "wind_score": {
        "label": "Potencial eólico",
        "short_label": "Eólico",
        "color": "#3E8DA8",
    },
}

CLUSTER_COLORS = {
    "Solar-dominant": "#F0A23A",
    "Wind-dominant": "#3E8DA8",
    "Hybrid-high": "#7057A6",
    "Lower-resource": "#8B9A94",
}

CLUSTER_LABELS = {
    "Solar-dominant": "Solar dominante",
    "Wind-dominant": "Eólico dominante",
    "Hybrid-high": "Híbrido alto",
    "Lower-resource": "Potencial bajo",
}


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

