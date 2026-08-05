import hashlib
import random
from datetime import datetime, timedelta

from renewable_atlas.domain import ClimateDataSource, ClimateObservation, GridPoint


class FakeClimateDataSource(ClimateDataSource):
    def __init__(self, seed_offset: int = 0, start_year: int = 2000, end_year: int = 2023):
        if start_year > end_year:
            raise ValueError("start_year must not be greater than end_year")
        self.seed_offset = seed_offset
        self.start_year = start_year
        self.end_year = end_year

    def fetch_observations(self, point: GridPoint) -> list[ClimateObservation]:
        observations = []
        start_date = datetime(self.start_year, 1, 1).date()
        end_date = datetime(self.end_year, 12, 31).date()

        current_date = start_date
        point_id = (
            int(hashlib.md5(f"{point.latitude},{point.longitude}".encode()).hexdigest(), 16) % 10000
        )

        while current_date <= end_date:
            seed = (point_id + current_date.toordinal() + self.seed_offset) % (2**31)
            random.seed(seed)

            sw_dwn = random.uniform(100, 300)
            dni = random.uniform(200, 800)
            ws_50m = random.uniform(2, 10)
            ws_100m = random.uniform(3, 12)

            obs = ClimateObservation(
                date=current_date,
                sw_dwn=sw_dwn,
                dni=dni,
                ws_50m=ws_50m,
                ws_100m=ws_100m,
            )
            observations.append(obs)
            current_date += timedelta(days=1)

        return observations
