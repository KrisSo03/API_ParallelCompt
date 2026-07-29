import pandas as pd
import numpy as np


class ScoringService:
    def score(
        self,
        indicators_df: pd.DataFrame,
        weight_solar: float = 0.5,
        weight_wind: float = 0.3,
        weight_hybrid: float = 0.2,
    ) -> pd.DataFrame:
        df = indicators_df.copy()

        # Min-max normalization for solar
        if "sw_dwn_mean" in df.columns:
            sw_min, sw_max = df["sw_dwn_mean"].min(), df["sw_dwn_mean"].max()
            if sw_max > sw_min:
                df["solar_score"] = (df["sw_dwn_mean"] - sw_min) / (sw_max - sw_min)
            else:
                df["solar_score"] = 0.5

        # Min-max normalization for wind
        if "ws_100m_mean" in df.columns:
            ws_min, ws_max = df["ws_100m_mean"].min(), df["ws_100m_mean"].max()
            if ws_max > ws_min:
                df["wind_score"] = (df["ws_100m_mean"] - ws_min) / (ws_max - ws_min)
            else:
                df["wind_score"] = 0.5

        # Hybrid score
        if "solar_score" in df.columns and "wind_score" in df.columns:
            df["hybrid_score"] = (
                weight_solar * df["solar_score"]
                + weight_wind * df["wind_score"]
                + weight_hybrid * (df["solar_score"] * df["wind_score"])
            )

        return df
