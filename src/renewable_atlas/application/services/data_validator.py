from dataclasses import dataclass

import pandas as pd


@dataclass
class ValidationReport:
    total_rows: int
    complete_rows: int
    completeness_ratio: float
    is_valid: bool


class DataValidator:
    def validate(
        self, df: pd.DataFrame, required_columns: list[str] | None = None
    ) -> ValidationReport:
        total_rows = len(df)
        columns = required_columns or list(df.columns)
        missing_columns = [column for column in columns if column not in df.columns]
        complete_rows = 0 if missing_columns else df.dropna(subset=columns).shape[0]
        completeness_ratio = complete_rows / total_rows if total_rows > 0 else 0

        is_valid = completeness_ratio >= 0.5

        return ValidationReport(
            total_rows=total_rows,
            complete_rows=complete_rows,
            completeness_ratio=completeness_ratio,
            is_valid=is_valid,
        )
