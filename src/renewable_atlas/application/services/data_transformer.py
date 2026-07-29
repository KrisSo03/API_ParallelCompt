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
            }
            for obs in observations
        ]
        return pd.DataFrame(data)

    @staticmethod
    def clean(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # Null out-of-range values
        for col in ["sw_dwn", "dni", "ws_50m", "ws_100m"]:
            if col in df.columns:
                if col == "sw_dwn":
                    df.loc[(df[col] < 0) | (df[col] > 400), col] = None
                elif col == "dni":
                    df.loc[(df[col] < 0) | (df[col] > 900), col] = None
                elif col in ["ws_50m", "ws_100m"]:
                    df.loc[(df[col] < 0) | (df[col] > 30), col] = None

        # Deduplicate
        df = df.drop_duplicates()

        # Drop fully empty rows
        df = df.dropna(how="all", subset=["sw_dwn", "dni", "ws_50m", "ws_100m"])

        # Sort by date
        if "date" in df.columns:
            df = df.sort_values("date").reset_index(drop=True)

        return df
