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
        sw_dwn_mean = self._mean(df, "sw_dwn")
        dni_mean = self._mean(df, "dni")
        ws_50m_mean = self._mean(df, "ws_50m")
        ws_100m_mean = self._mean(df, "ws_100m")

        solar_score = (
            self._normalize(sw_dwn_mean, df["sw_dwn"].dropna()) if "sw_dwn" in df.columns else 0.0
        )
        wind_score = (
            self._normalize(ws_100m_mean, df["ws_100m"].dropna())
            if "ws_100m" in df.columns
            else 0.0
        )
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
            ws_10m_mean=self._mean(df, "ws_10m"),
            sw_diff_mean=self._mean(df, "sw_diff"),
            clr_sky_sw_dwn_mean=self._mean(df, "clr_sky_sw_dwn"),
            allsky_kt_mean=self._mean(df, "allsky_kt"),
            wd_10m_mean=self._mean(df, "wd_10m"),
            wd_50m_mean=self._mean(df, "wd_50m"),
            t2m_mean=self._mean(df, "t2m"),
            t2m_max_mean=self._mean(df, "t2m_max"),
            t2m_min_mean=self._mean(df, "t2m_min"),
            t2mdew_mean=self._mean(df, "t2mdew"),
            ps_mean=self._mean(df, "ps"),
            rh2m_mean=self._mean(df, "rh2m"),
            qv2m_mean=self._mean(df, "qv2m"),
            prectotcorr_mean=self._mean(df, "prectotcorr"),
            cloud_amt_mean=self._mean(df, "cloud_amt"),
        )

    @staticmethod
    def _mean(df: pd.DataFrame, column: str) -> float:
        if column not in df.columns or df[column].dropna().empty:
            return 0.0
        return float(df[column].mean())

    @staticmethod
    def _normalize(value: float, series: pd.Series) -> float:
        if len(series) == 0:
            return 0.0

        s_min = float(series.min())
        s_max = float(series.max())
        if s_max <= s_min:
            return 0.5
        return float((value - s_min) / (s_max - s_min))
