import pandas as pd
import numpy as np
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

        return RenewableIndicators(
            point_id=point_id,
            latitude=latitude,
            longitude=longitude,
            country=country,
            sw_dwn_mean=sw_dwn_mean,
            dni_mean=dni_mean,
            ws_50m_mean=ws_50m_mean,
            ws_100m_mean=ws_100m_mean,
            solar_score=0.0,
            wind_score=0.0,
            hybrid_score=0.0,
        )
