import pandas as pd
from dataclasses import dataclass


@dataclass
class ValidationReport:
    total_rows: int
    complete_rows: int
    completeness_ratio: float
    is_valid: bool


class DataValidator:
    def validate(self, df: pd.DataFrame) -> ValidationReport:
        total_rows = len(df)
        complete_rows = df.dropna().shape[0]
        completeness_ratio = complete_rows / total_rows if total_rows > 0 else 0

        is_valid = completeness_ratio >= 0.5

        return ValidationReport(
            total_rows=total_rows,
            complete_rows=complete_rows,
            completeness_ratio=completeness_ratio,
            is_valid=is_valid,
        )
