import pandas as pd
from renewable_atlas.domain import RenewableIndicators


class IndicatorCalculator:
    def calculate(
        self,
        point_id: int,
        latitude: float,
        longitude: float,
        country: str,
        df: pd.DataFrame,
    ) -> RenewableIndicators:
        sw_dwn_mean = float(df["sw_dwn"].mean()) if "sw_dwn" in df.columns else 0.0
        dni_mean = float(df["dni"].mean()) if "dni" in df.columns else 0.0
        ws_50m_mean = float(df["ws_50m"].mean()) if "ws_50m" in df.columns else 0.0
        ws_100m_mean = float(df["ws_100m"].mean()) if "ws_100m" in df.columns else 0.0

        solar_score = self._normalize(sw_dwn_mean, df["sw_dwn"].dropna()) if "sw_dwn" in df.columns else 0.0
        wind_score = self._normalize(ws_100m_mean, df["ws_100m"].dropna()) if "ws_100m" in df.columns else 0.0
        hybrid_score = 0.5 * solar_score + 0.3 * wind_score + 0.2 * (solar_score * wind_score)

        return RenewableIndicators(
            point_id=point_id,
            latitude=latitude,
            longitude=longitude,
            country=country,
            sw_dwn_mean=sw_dwn_mean,
            dni_mean=dni_mean,
            ws_50m_mean=ws_50m_mean,
            ws_100m_mean=ws_100m_mean,
            solar_score=solar_score,
            wind_score=wind_score,
            hybrid_score=hybrid_score,
        )

    @staticmethod
    def _normalize(value: float, series: pd.Series) -> float:
        if len(series) == 0:
            return 0.0

        s_min = float(series.min())
        s_max = float(series.max())
        if s_max <= s_min:
            return 0.5
        return float((value - s_min) / (s_max - s_min))
