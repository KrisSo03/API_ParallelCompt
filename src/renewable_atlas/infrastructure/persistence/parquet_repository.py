import pandas as pd
from pathlib import Path
import pyarrow.parquet as pq
from renewable_atlas.domain import DataRepository


class ParquetDataRepository(DataRepository):
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, key: str) -> Path:
        return self.base_dir / f"{key}.parquet"

    def save(self, data: pd.DataFrame, key: str) -> None:
        path = self._get_path(key)
        data.to_parquet(path)

    def load(self, key: str) -> pd.DataFrame:
        path = self._get_path(key)
        return pd.read_parquet(path)

    def exists(self, key: str) -> bool:
        return self._get_path(key).exists()

    def metadata(self, key: str) -> dict:
        path = self._get_path(key)
        if not path.exists():
            return {}

        table = pq.read_table(path)
        return {
            "columns": table.column_names,
            "num_rows": table.num_rows,
            "file_size_mb": path.stat().st_size / (1024 * 1024),
        }
