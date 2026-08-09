from dataclasses import dataclass

import numpy as np
import pandas as pd

from renewable_atlas.domain import ClimateObservation


@dataclass
class ValidationReport:
    total_rows: int
    complete_rows: int
    completeness_ratio: float
    is_valid: bool

    duplicate_rows: int
    duplicate_ratio: float

    available_columns: list[str]
    fully_empty_columns: list[str]
    missing_ratio_by_column: dict[str, float]

    nan_count_by_column: dict[str, int]
    infinite_count_by_column: dict[str, int]
    sentinel_count_by_column: dict[str, int]

    invalid_date_rows: int
    duplicate_date_rows: int
    dates_are_sorted: bool

    out_of_range_count_by_column: dict[str, int]


class DataValidator:
    def validate(
        self,
        df: pd.DataFrame,
        required_columns: list[str] | None = None,
    ) -> ValidationReport:
        total_rows = len(df)

        columns = required_columns or list(df.columns)
        missing_columns = [
            column for column in columns
            if column not in df.columns
        ]

        complete_rows = (
            0
            if missing_columns
            else df.dropna(subset=columns).shape[0]
        )

        completeness_ratio = (
            complete_rows / total_rows
            if total_rows > 0
            else 0
        )

        # Se mantiene el criterio existente por ahora.
        is_valid = completeness_ratio >= 0.5

        duplicate_rows = int(df.duplicated().sum())
        duplicate_ratio = duplicate_rows / total_rows if total_rows > 0 else 0

        available_columns = list(df.columns)

        fully_empty_columns = [
            col for col in df.columns
            if df[col].isna().all()
        ]

        missing_ratio_by_column = {
            col: float(df[col].isna().mean())
            for col in df.columns
        }

        nan_count_by_column = {
            col: int(df[col].isna().sum())
            for col in df.columns
        }

        infinite_count_by_column = {}
        sentinel_count_by_column = {}

        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                infinite_count_by_column[col] = int(
                    np.isinf(
                        df[col].to_numpy(
                            dtype=float,
                            na_value=np.nan,
                        )
                    ).sum()
                )
                sentinel_count_by_column[col] = int(
                    (df[col] == -999).sum()
                )
            else:
                infinite_count_by_column[col] = 0
                sentinel_count_by_column[col] = 0

        invalid_date_rows = 0
        duplicate_date_rows = 0
        dates_are_sorted = True

        if "date" in df.columns:
            parsed_dates = pd.to_datetime(
                df["date"],
                errors="coerce",
            )

            invalid_date_rows = int(
                parsed_dates.isna().sum()
            )

            valid_dates = parsed_dates.dropna()

            duplicate_date_rows = int(
                valid_dates.duplicated().sum()
            )

            dates_are_sorted = bool(
                valid_dates.is_monotonic_increasing
            )

        out_of_range_count_by_column = {}

        for (
            col,
            (min_value, max_value),
        ) in ClimateObservation.PLAUSIBLE_RANGES.items():
            if col in df.columns:
                numeric_values = pd.to_numeric(
                    df[col],
                    errors="coerce",
                )

                out_of_range_count_by_column[col] = int(
                    (
                        (numeric_values < min_value)
                        | (numeric_values > max_value)
                    ).sum()
                )

        return ValidationReport(
            total_rows=total_rows,
            complete_rows=complete_rows,
            completeness_ratio=completeness_ratio,
            is_valid=is_valid,
            duplicate_rows=duplicate_rows,
            duplicate_ratio=duplicate_ratio,
            available_columns=available_columns,
            fully_empty_columns=fully_empty_columns,
            missing_ratio_by_column=missing_ratio_by_column,
            nan_count_by_column=nan_count_by_column,
            infinite_count_by_column=infinite_count_by_column,
            sentinel_count_by_column=sentinel_count_by_column,
            invalid_date_rows=invalid_date_rows,
            duplicate_date_rows=duplicate_date_rows,
            dates_are_sorted=dates_are_sorted,
            out_of_range_count_by_column=out_of_range_count_by_column,
        )
