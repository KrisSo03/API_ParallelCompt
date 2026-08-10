"""Validation rules for experiment outputs consumed by the dashboard."""

from __future__ import annotations

from typing import Any

import pandas as pd


class DashboardDataError(ValueError):
    """Raised when an experiment cannot be displayed safely."""


REQUIRED_INDICATOR_COLUMNS = {
    "point_id",
    "latitude",
    "longitude",
    "country",
    "sw_dwn_mean",
    "dni_mean",
    "ws_50m_mean",
    "ws_100m_mean",
    "solar_score",
    "wind_score",
    "hybrid_score",
    "cluster_id",
}

SCORE_COLUMNS = ("solar_score", "wind_score", "hybrid_score")


def validate_manifest(manifest: dict[str, Any]) -> None:
    if not isinstance(manifest, dict):
        raise DashboardDataError("El manifiesto no contiene un objeto JSON válido.")
    if manifest.get("status") != "success":
        detail = manifest.get("error") or "la corrida no terminó correctamente"
        raise DashboardDataError(f"La corrida seleccionada no fue exitosa: {detail}.")


def validate_indicators(indicators: pd.DataFrame) -> None:
    if indicators.empty:
        raise DashboardDataError("El archivo de indicadores no contiene puntos.")

    missing = sorted(REQUIRED_INDICATOR_COLUMNS - set(indicators.columns))
    if missing:
        raise DashboardDataError(
            "Faltan columnas obligatorias en indicators.parquet: " + ", ".join(missing)
        )

    identity_columns = ["point_id", "latitude", "longitude", "country", "cluster_id"]
    if indicators[identity_columns].isnull().any().any():
        raise DashboardDataError("Existen puntos sin identidad, coordenadas, país o cluster.")

    latitude = pd.to_numeric(indicators["latitude"], errors="coerce")
    longitude = pd.to_numeric(indicators["longitude"], errors="coerce")
    if latitude.isna().any() or not latitude.between(-90, 90).all():
        raise DashboardDataError("La columna latitude contiene valores inválidos.")
    if longitude.isna().any() or not longitude.between(-180, 180).all():
        raise DashboardDataError("La columna longitude contiene valores inválidos.")

    for column in SCORE_COLUMNS:
        values = pd.to_numeric(indicators[column], errors="coerce")
        if values.isna().all():
            raise DashboardDataError(f"La columna {column} no contiene valores numéricos.")
        valid_values = values.dropna()
        if not valid_values.between(0, 1).all():
            raise DashboardDataError(f"La columna {column} contiene valores fuera de [0, 1].")


def validate_profiles(profiles: list[dict[str, Any]], cluster_ids: set[int]) -> None:
    if not isinstance(profiles, list) or not profiles:
        raise DashboardDataError("cluster_profiles.json no contiene perfiles.")

    required = {"cluster_id", "label", "description", "size", "centroid"}
    profile_ids: list[int] = []
    for index, profile in enumerate(profiles, start=1):
        if not isinstance(profile, dict):
            raise DashboardDataError(f"El perfil {index} no es un objeto JSON válido.")
        missing = sorted(required - set(profile))
        if missing:
            raise DashboardDataError(
                f"Al perfil {index} le faltan campos: " + ", ".join(missing)
            )
        try:
            profile_ids.append(int(profile["cluster_id"]))
        except (TypeError, ValueError) as exc:
            raise DashboardDataError(f"El perfil {index} tiene un cluster_id inválido.") from exc

    if len(profile_ids) != len(set(profile_ids)):
        raise DashboardDataError("Existen perfiles repetidos para un mismo cluster_id.")

    missing_profiles = sorted(cluster_ids - set(profile_ids))
    if missing_profiles:
        values = ", ".join(str(value) for value in missing_profiles)
        raise DashboardDataError(f"No existen perfiles para los clusters: {values}.")


def validate_row_count(indicators: pd.DataFrame, manifest: dict[str, Any]) -> None:
    expected = manifest.get("point_count")
    if expected is None:
        return
    try:
        expected_count = int(expected)
    except (TypeError, ValueError) as exc:
        raise DashboardDataError("point_count no es válido en manifest.json.") from exc
    if len(indicators) != expected_count:
        raise DashboardDataError(
            f"El manifiesto declara {expected_count} puntos, pero se encontraron {len(indicators)}."
        )

