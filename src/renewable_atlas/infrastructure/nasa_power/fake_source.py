import hashlib
from datetime import datetime, timedelta
import random
from renewable_atlas.domain import GridPoint, ClimateDataSource, ClimateObservation


class FakeClimateDataSource(ClimateDataSource):
    def __init__(self, seed_offset: int = 0):
        self.seed_offset = seed_offset

    def fetch_observations(self, point: GridPoint) -> list[ClimateObservation]:
        observations = []
        start_date = datetime(2000, 1, 1).date()
        end_date = datetime(2023, 12, 31).date()

        current_date = start_date
        point_id = int(
            hashlib.md5(f"{point.latitude},{point.longitude}".encode()).hexdigest(), 16
        ) % 10000

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
