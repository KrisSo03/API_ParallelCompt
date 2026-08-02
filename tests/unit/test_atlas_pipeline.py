from renewable_atlas.application.pipelines.atlas_pipeline import AtlasPipeline
from renewable_atlas.domain import GridPoint, ClimateObservation


class DummyRepository:
    def __init__(self):
        self.saved = []

    def save(self, data, key):
        self.saved.append((key, data))


class DummyDataSource:
    def __init__(self):
        self.calls = 0

    def fetch_observations(self, point):
        self.calls += 1
        if point.latitude > 0:
            raise RuntimeError("temporary failure")
        return [ClimateObservation(date="2020-01-01", sw_dwn=1.0, dni=2.0, ws_50m=3.0, ws_100m=4.0)]


class DummyClusteringService:
    def cluster(self, indicators_df):
        return [], []


class DummyInterpretationService:
    def interpret(self, profiles):
        return profiles


def test_download_continues_when_one_point_fails():
    source = DummyDataSource()
    repository = DummyRepository()
    pipeline = AtlasPipeline(
        data_source=source,
        repository=repository,
        clustering_service=DummyClusteringService(),
        interpretation_service=DummyInterpretationService(),
    )

    points = [GridPoint(latitude=1.0, longitude=2.0, country="Guatemala"), GridPoint(latitude=-1.0, longitude=-2.0, country="Belize")]

    observations_by_point = pipeline.download(points)

    assert len(observations_by_point) == 2
    assert repository.saved[0][0] == "raw_observations"
    assert len(repository.saved[0][1]) == 1
