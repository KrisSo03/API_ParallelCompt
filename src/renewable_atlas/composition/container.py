from renewable_atlas.application.pipelines import AtlasPipeline
from renewable_atlas.application.services import ClusteringService, ClusterInterpretationService
from renewable_atlas.config import Settings
from renewable_atlas.domain import (
    ClimateDataSource,
    ClusteringStrategy,
    DataRepository,
)
from renewable_atlas.infrastructure import (
    BenchmarkService,
    DaskProcessor,
    FakeClimateDataSource,
    KMeansClusteringStrategy,
    NASAPowerDataSource,
    ParquetDataRepository,
    SequentialProcessor,
)


class CompositionRoot:
    def __init__(self, settings: Settings):
        self.settings = settings

    def build_climate_data_source(self, use_fake: bool = False) -> ClimateDataSource:
        if use_fake:
            return FakeClimateDataSource(
                seed_offset=self.settings.execution.random_seed,
                start_year=self.settings.date_range.start_year,
                end_year=self.settings.date_range.end_year,
            )
        return NASAPowerDataSource(
            base_url=self.settings.nasa_power.base_url,
            timeout=self.settings.nasa_power.timeout_seconds,
            max_retries=self.settings.nasa_power.max_retries,
            start_year=self.settings.date_range.start_year,
            end_year=self.settings.date_range.end_year,
        )

    def build_data_repository(self) -> DataRepository:
        return ParquetDataRepository(self.settings.paths.data_dir)

    def build_clustering_strategy(self) -> ClusteringStrategy:
        return KMeansClusteringStrategy(
            n_clusters=self.settings.clustering.n_clusters,
            random_state=self.settings.clustering.random_state,
        )

    def build_clustering_service(self) -> ClusteringService:
        strategy = self.build_clustering_strategy()
        return ClusteringService(strategy)

    def build_cluster_interpretation_service(self) -> ClusterInterpretationService:
        return ClusterInterpretationService()

    def build_atlas_pipeline(self, use_fake: bool = False) -> AtlasPipeline:
        data_source = self.build_climate_data_source(use_fake)
        repository = self.build_data_repository()
        clustering_service = self.build_clustering_service()
        interpretation_service = self.build_cluster_interpretation_service()

        return AtlasPipeline(
            data_source=data_source,
            repository=repository,
            clustering_service=clustering_service,
            interpretation_service=interpretation_service,
        )

    def build_sequential_processor(self):
        return SequentialProcessor()

    def build_dask_processor(self, num_workers: int = 4, scheduler: str = "processes"):
        return DaskProcessor(num_workers=num_workers, scheduler=scheduler)

    def build_benchmark_service(self) -> BenchmarkService:
        return BenchmarkService()
