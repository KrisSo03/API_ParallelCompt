import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
from renewable_atlas.domain import GridPoint, ClimateDataSource, ClimateObservation
from .response_parser import parse_point_response
from .exceptions import NASAPowerException

logger = logging.getLogger(__name__)


class NASAPowerDataSource(ClimateDataSource):
    def __init__(self, base_url: str, timeout: int = 30, max_retries: int = 3):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_observations(self, point: GridPoint) -> list[ClimateObservation]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                params = {
                    "parameters": "SW_DWN,DNI,WS50M,WS100M",
                    "community": "sb",
                    "longitude": str(point.longitude),
                    "latitude": str(point.latitude),
                    "start": "2000",
                    "end": "2023",
                    "format": "json",
                }

                response = client.get(
                    f"{self.base_url}temporal/daily",
                    params=params,
                )
                response.raise_for_status()

                data = response.json()
                observations = parse_point_response(data)
                logger.info(f"Fetched {len(observations)} observations for {point.country}")
                return observations

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503:
                logger.warning(f"NASA POWER service unavailable, retrying...")
                raise
            raise NASAPowerException(f"HTTP error {e.response.status_code}: {e}") from e
        except httpx.RequestError as e:
            raise NASAPowerException(f"Request failed: {e}") from e
