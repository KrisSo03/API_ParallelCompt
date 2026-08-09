"""Data preparation and overview metrics for dashboard views."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class OverviewMetrics:
    points: int
    countries: int
    clusters: int
    average_score: float
    best_country: str


def enrich_indicators(
    indicators: pd.DataFrame, profiles: list[dict[str, Any]]
) -> pd.DataFrame:
    """Attach the human-readable profile label to every geographic point."""
    enriched = indicators.copy()
    labels = {
        int(profile["cluster_id"]): str(profile.get("label", f"Cluster {profile['cluster_id']}"))
        for profile in profiles
    }
    enriched["cluster_id"] = pd.to_numeric(enriched["cluster_id"]).astype(int)
    enriched["cluster_label"] = enriched["cluster_id"].map(labels).fillna("Sin perfil")
    return enriched


def filter_indicators(
    indicators: pd.DataFrame,
    countries: list[str] | None = None,
    cluster_ids: list[int] | None = None,
) -> pd.DataFrame:
    filtered = indicators.copy()
    if countries is not None:
        filtered = filtered[filtered["country"].isin(countries)]
    if cluster_ids is not None:
        filtered = filtered[filtered["cluster_id"].isin(cluster_ids)]
    return filtered.reset_index(drop=True)


def overview_metrics(indicators: pd.DataFrame, metric: str) -> OverviewMetrics:
    if indicators.empty:
        return OverviewMetrics(0, 0, 0, 0.0, "Sin datos")

    country_scores = indicators.groupby("country", dropna=False)[metric].mean().sort_values()
    best_country = str(country_scores.index[-1]) if not country_scores.empty else "Sin datos"
    return OverviewMetrics(
        points=len(indicators),
        countries=int(indicators["country"].nunique()),
        clusters=int(indicators["cluster_id"].nunique()),
        average_score=float(indicators[metric].mean()),
        best_country=best_country,
    )


def featured_profile_id(indicators: pd.DataFrame, metric: str) -> int:
    """Choose the strongest visible cluster for the active metric."""
    if indicators.empty:
        raise ValueError("Cannot select a featured profile from an empty dataframe")
    averages = indicators.groupby("cluster_id")[metric].mean()
    return int(averages.idxmax())


def profile_scores(indicators: pd.DataFrame, cluster_id: int) -> dict[str, float]:
    """Return normalized score averages for one cluster in the visible selection."""
    rows = indicators[indicators["cluster_id"] == cluster_id]
    if rows.empty:
        return {"solar_score": 0.0, "wind_score": 0.0, "hybrid_score": 0.0}
    return {
        column: float(rows[column].mean())
        for column in ("solar_score", "wind_score", "hybrid_score")
    }


def country_comparison(indicators: pd.DataFrame, countries: list[str]) -> pd.DataFrame:
    """Aggregate the three user-facing potential scores for selected countries."""
    selected = indicators[indicators["country"].isin(countries)]
    return (
        selected.groupby("country", as_index=False)[
            ["solar_score", "wind_score", "hybrid_score"]
        ]
        .mean()
        .sort_values("country")
        .reset_index(drop=True)
    )


def performance_summary(summary: pd.DataFrame) -> pd.DataFrame:
    """Summarize repeated successful runs and derive speedup and efficiency."""
    required = {"workers", "elapsed_seconds"}
    if summary.empty or not required.issubset(summary.columns):
        return pd.DataFrame()
    successful = summary.copy()
    if "status" in successful.columns:
        successful = successful[successful["status"] == "success"]
    successful["workers"] = pd.to_numeric(successful["workers"], errors="coerce")
    successful["elapsed_seconds"] = pd.to_numeric(
        successful["elapsed_seconds"], errors="coerce"
    )
    successful = successful.dropna(subset=["workers", "elapsed_seconds"])
    if successful.empty:
        return pd.DataFrame()
    result = (
        successful.groupby("workers", as_index=False)
        .agg(
            tiempo_mediano=("elapsed_seconds", "median"),
            tiempo_promedio=("elapsed_seconds", "mean"),
            repeticiones=("elapsed_seconds", "size"),
        )
        .sort_values("workers")
    )
    baseline_rows = result[result["workers"] == 1]
    if baseline_rows.empty:
        result["speedup"] = pd.NA
        result["eficiencia"] = pd.NA
    else:
        baseline = float(baseline_rows.iloc[0]["tiempo_mediano"])
        result["speedup"] = baseline / result["tiempo_mediano"]
        result["eficiencia"] = result["speedup"] / result["workers"]
    result["workers"] = result["workers"].astype(int)
    return result.reset_index(drop=True)
