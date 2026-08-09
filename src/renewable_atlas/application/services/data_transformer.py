import pandas as pd

from renewable_atlas.domain import ClimateObservation


class DataTransformer:
    @staticmethod
    def to_dataframe(observations: list[ClimateObservation]) -> pd.DataFrame:
        data = [
            {
                "date": obs.date,
                "sw_dwn": obs.sw_dwn,
                "dni": obs.dni,
                "ws_50m": obs.ws_50m,
                "ws_100m": obs.ws_100m,
                "ws_10m": obs.ws_10m,
                "sw_diff": obs.sw_diff,
                "clr_sky_sw_dwn": obs.clr_sky_sw_dwn,
                "allsky_kt": obs.allsky_kt,
                "wd_100m": obs.wd_100m,
                "wd_50m": obs.wd_50m,
                "wd_10m": obs.wd_10m,
                "t2m": obs.t2m,
                "t2m_max": obs.t2m_max,
                "t2m_min": obs.t2m_min,
                "t2mdew": obs.t2mdew,
                "ps": obs.ps,
                "rh2m": obs.rh2m,
                "qv2m": obs.qv2m,
                "prectotcorr": obs.prectotcorr,
                "cloud_amt": obs.cloud_amt,
            }
            for obs in observations
        ]
        return pd.DataFrame(data)

    @staticmethod
    def clean(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        available_columns = [
            col
            for col in [
                "sw_dwn",
                "dni",
                "ws_50m",
                "ws_100m",
                "ws_10m",
                "sw_diff",
                "clr_sky_sw_dwn",
                "allsky_kt",
                "wd_100m",
                "wd_50m",
                "wd_10m",
                "t2m",
                "t2m_max",
                "t2m_min",
                "t2mdew",
                "ps",
                "rh2m",
                "qv2m",
                "prectotcorr",
                "cloud_amt",
            ]
            if col in df.columns
        ]

        for col in available_columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            if col in ClimateObservation.PLAUSIBLE_RANGES:
                minimum, maximum = ClimateObservation.PLAUSIBLE_RANGES[col]
                df.loc[~df[col].between(minimum, maximum), col] = None

        df = df.drop_duplicates()

        if available_columns:
            df = df.dropna(how="all", subset=available_columns)

        if "date" in df.columns:
            df = df.sort_values("date").reset_index(drop=True)

        return df
