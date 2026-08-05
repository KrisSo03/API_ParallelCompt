from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class NasaPowerSettings(BaseSettings):
    base_url: str = Field(default="https://power.larc.nasa.gov/api/")
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
            raise ValueError(
                "DATE_RANGE_START_YEAR must be less than or equal to DATE_RANGE_END_YEAR"
            )


class GridSettings(BaseSettings):
    size: int = Field(default=80, ge=1)
    enable_sampling: bool = Field(default=True)
    sample_size: int = Field(default=80, ge=1)

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

    def __init__(self, **data):
        if "worker_counts" in data and isinstance(data["worker_counts"], str):
            data["worker_counts"] = [int(x.strip()) for x in data["worker_counts"].split(",")]
        super().__init__(**data)


class PathSettings(BaseSettings):
    data_dir: str = Field(default="./data")
    results_dir: str = Field(default="./results")
    logs_dir: str = Field(default="./outputs/logs")

    model_config = SettingsConfigDict(env_prefix="PATH_", env_file=".env", extra="ignore")


class ExecutionSettings(BaseSettings):
    source: str = Field(default="fake", pattern="^(fake|nasa)$")
    scheduler: str = Field(default="processes", pattern="^(processes|threads)$")
    random_seed: int = Field(default=42)

    model_config = SettingsConfigDict(env_prefix="EXECUTION_", env_file=".env", extra="ignore")


class Settings:
    def __init__(self):
        self.nasa_power = NasaPowerSettings()
        self.date_range = DateRangeSettings()
        self.grid = GridSettings()
        self.scoring = ScoringSettings()
        self.clustering = ClusteringSettings()
        self.benchmark = BenchmarkSettings()
        self.execution = ExecutionSettings()
        self.paths = PathSettings()

    def snapshot(self) -> dict:
        return {
            "nasa_power": self.nasa_power.model_dump(),
            "date_range": self.date_range.model_dump(),
            "grid": self.grid.model_dump(),
            "scoring": self.scoring.model_dump(),
            "clustering": self.clustering.model_dump(),
            "benchmark": self.benchmark.model_dump(),
            "execution": self.execution.model_dump(),
            "paths": self.paths.model_dump(),
        }

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv()
        return cls()
