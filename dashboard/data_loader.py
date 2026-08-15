"""Discover and load local or Kabré experiment results."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from dashboard.validators import (
    DashboardDataError,
    validate_indicators,
    validate_manifest,
    validate_profiles,
    validate_row_count,
)

WORKERS_PATTERN = re.compile(r"workers-(\d+)$")
RUN_PATTERN = re.compile(r"run-(\d+)$")


@dataclass(frozen=True)
class RunReference:
    workers: int
    repeat: int
    path: Path


@dataclass
class RunData:
    reference: RunReference
    indicators: pd.DataFrame
    profiles: list[dict[str, Any]]
    manifest: dict[str, Any]


def discover_worker_counts(experiment_dir: Path) -> list[int]:
    if not experiment_dir.is_dir():
        return []
    worker_counts = []
    for path in experiment_dir.iterdir():
        match = WORKERS_PATTERN.fullmatch(path.name) if path.is_dir() else None
        if match:
            worker_counts.append(int(match.group(1)))
    return sorted(set(worker_counts))


def discover_runs(experiment_dir: Path, workers: int) -> list[RunReference]:
    workers_dir = experiment_dir / f"workers-{workers:03d}"
    if not workers_dir.is_dir():
        return []
    references = []
    for path in workers_dir.iterdir():
        match = RUN_PATTERN.fullmatch(path.name) if path.is_dir() else None
        if match:
            references.append(
                RunReference(workers=workers, repeat=int(match.group(1)), path=path)
            )
    return sorted(references, key=lambda reference: reference.repeat)


def load_run(reference: RunReference) -> RunData:
    indicators_path = reference.path / "indicators.parquet"
    profiles_path = reference.path / "cluster_profiles.json"
    manifest_path = reference.path / "manifest.json"

    for path in (indicators_path, profiles_path, manifest_path):
        if not path.is_file():
            raise DashboardDataError(f"No se encontró el archivo requerido: {path.name}.")

    try:
        indicators = pd.read_parquet(indicators_path)
    except Exception as exc:
        raise DashboardDataError(f"No fue posible leer {indicators_path.name}: {exc}") from exc

    # Compatibility with experiments generated before PR #8.
    if "cluster" in indicators.columns and "cluster_id" not in indicators.columns:
        indicators = indicators.rename(columns={"cluster": "cluster_id"})

    profiles = _read_json(profiles_path)
    manifest = _read_json(manifest_path)

    validate_manifest(manifest)
    validate_indicators(indicators)
    cluster_ids = set(pd.to_numeric(indicators["cluster_id"]).astype(int).unique())
    validate_profiles(profiles, cluster_ids)
    validate_row_count(indicators, manifest)

    return RunData(
        reference=reference,
        indicators=indicators,
        profiles=profiles,
        manifest=manifest,
    )


def load_summary(experiment_dir: Path) -> pd.DataFrame:
    summary_paths = sorted(experiment_dir.glob("summary*.csv"))
    if not summary_paths:
        return pd.DataFrame()

    frames = []
    for path in summary_paths:
        try:
            frame = pd.read_csv(path)
        except Exception as exc:
            raise DashboardDataError(f"No fue posible leer {path.name}: {exc}") from exc
        frame["summary_file"] = path.name
        frames.append(frame)

    summary = pd.concat(frames, ignore_index=True)
    keys = [column for column in ("workers", "repeat", "run_dir") if column in summary]
    if keys:
        summary = summary.drop_duplicates(subset=keys, keep="last")
    return summary.sort_values(keys).reset_index(drop=True) if keys else summary


def _read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise DashboardDataError(f"No fue posible leer {path.name}: {exc}") from exc

