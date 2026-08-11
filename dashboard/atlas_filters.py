"""Selection rules for the interactive atlas."""

from __future__ import annotations

import pandas as pd


def select_featured_points(
    indicators: pd.DataFrame,
    metric: str,
    limit_per_country: int,
) -> pd.DataFrame:
    """Return the best N points for every country using a stable ordering."""
    if metric not in indicators.columns:
        raise ValueError(f"Unknown atlas metric: {metric}")
    if limit_per_country < 1:
        raise ValueError("limit_per_country must be at least 1")
    if indicators.empty:
        return indicators.copy()

    return (
        indicators.sort_values(
            ["country", metric, "point_id"],
            ascending=[True, False, True],
            kind="stable",
        )
        .groupby("country", sort=False, group_keys=False)
        .head(limit_per_country)
        .reset_index(drop=True)
    )


def point_label(row: pd.Series) -> str:
    """Build the user-facing identifier shared by the map and table."""
    return f"{row['country']} · Punto {int(row['point_id'])}"
