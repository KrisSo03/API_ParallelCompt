import logging
from urllib.parse import urljoin

import httpx
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from renewable_atlas.domain import ClimateDataSource, ClimateObservation, GridPoint

from .exceptions import NASAPowerException
from .response_parser import parse_point_response

DEFAULT_PARAMETERS = (
    "ALLSKY_SFC_SW_DWN,ALLSKY_SFC_SW_DNI,ALLSKY_SFC_SW_DIFF,CLRSKY_SFC_SW_DWN,"
    "ALLSKY_KT,WS10M,WS50M,WD10M,WD50M,T2M,T2M_MAX,T2M_MIN,T2MDEW,PS,RH2M,QV2M,"
    "PRECTOTCORR,CLOUD_AMT"
)

logger = logging.getLogger(__name__)


class NASAPowerDataSource(ClimateDataSource):
    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff_factor: float = 2.0,
        start_year: int = 2000,
        end_year: int = 2023,
    ):
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff_factor = retry_backoff_factor
        self.start_year = start_year
        self.end_year = end_year

    def fetch_observations(self, point: GridPoint) -> list[ClimateObservation]:
        try:
            retrying = Retrying(
                stop=stop_after_attempt(self.max_retries),
                wait=wait_exponential(multiplier=self.retry_backoff_factor, min=1, max=30),
                retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
                reraise=True,
            )
            response = retrying(self._request, point)
            observations = parse_point_response(response.json())
            if not observations:
                raise NASAPowerException(f"NASA POWER returned no observations for {point.country}")
            logger.info("Fetched %s observations for %s", len(observations), point.country)
            return observations

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503:
                logger.warning("NASA POWER service unavailable after retries")
                raise
            raise NASAPowerException(f"HTTP error {e.response.status_code}: {e}") from e
        except httpx.RequestError as e:
            raise NASAPowerException(f"Request failed: {e}") from e

    def _request(self, point: GridPoint) -> httpx.Response:
        params = {
            "parameters": DEFAULT_PARAMETERS,
            "community": "RE",
            "longitude": str(point.longitude),
            "latitude": str(point.latitude),
            "start": f"{self.start_year}0101",
            "end": f"{self.end_year}1231",
            "format": "JSON",
        }
        endpoint = urljoin(self.base_url, "temporal/daily/point")
        with httpx.Client(timeout=self.timeout, proxy=None, trust_env=False) as client:
            response = client.get(endpoint, params=params)
            response.raise_for_status()
            return response
