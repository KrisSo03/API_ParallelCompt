from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from dotenv import load_dotenv
from pathlib import Path


class NasaPowerSettings(BaseSettings):
    base_url: str = Field(default="https://power.larc.nasa.gov/api/v1/")
    timeout_seconds: int = Field(default=30)
    max_retries: int = Field(default=3)
    retry_backoff_factor: float = Field(default=2.0)

    model_config = SettingsConfigDict(env_prefix="NASA_POWER_", env_file=".env", extra="ignore")


class DateRangeSettings(BaseSettings):
    start_year: int = Field(default=2000)
    end_year: int = Field(default=2023)

    model_config = SettingsConfigDict(env_prefix="DATE_RANGE_", env_file=".env", extra="ignore")

    def model_post_init(self, __context):
        if self.start_year > self.end_year:
            raise ValueError("DATE_RANGE_START_YEAR must be less than or equal to DATE_RANGE_END_YEAR")


class GridSettings(BaseSettings):
    size: int = Field(default=80)
    enable_sampling: bool = Field(default=True)
    sample_size: int = Field(default=80)

    model_config = SettingsConfigDict(env_prefix="GRID_", env_file=".env", extra="ignore")


class ScoringSettings(BaseSettings):
    weight_solar: float = Field(default=0.5)
    weight_wind: float = Field(default=0.3)
    weight_hybrid: float = Field(default=0.2)

    model_config = SettingsConfigDict(env_prefix="SCORING_", env_file=".env", extra="ignore")


class ClusteringSettings(BaseSettings):
    n_clusters: int = Field(default=4)
    random_state: int = Field(default=42)

    model_config = SettingsConfigDict(env_prefix="CLUSTERING_", env_file=".env", extra="ignore")


class BenchmarkSettings(BaseSettings):
    worker_counts: list[int] = Field(default=[1, 2, 4, 8])
    repeats_per_config: int = Field(default=3)

    model_config = SettingsConfigDict(
        env_prefix="BENCHMARK_",
        env_file=".env",
        extra="ignore",
        enable_decoding=False,
    )

    @field_validator("worker_counts", mode="before")
    @classmethod
    def _parse_worker_counts(cls, value):
        if isinstance(value, str):
            cleaned = value.strip().strip("[]")
            return [int(x.strip()) for x in cleaned.split(",") if x.strip()]
        return value


class PathSettings(BaseSettings):
    data_dir: str = Field(default="./data")
    results_dir: str = Field(default="./results")
    logs_dir: str = Field(default="./outputs/logs")

    model_config = SettingsConfigDict(env_prefix="PATH_", env_file=".env", extra="ignore")


class Settings:
    def __init__(self):
        self.nasa_power = NasaPowerSettings()
        self.date_range = DateRangeSettings()
        self.grid = GridSettings()
        self.scoring = ScoringSettings()
        self.clustering = ClusteringSettings()
        self.benchmark = BenchmarkSettings()
        self.paths = PathSettings()

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv()
        return cls()
