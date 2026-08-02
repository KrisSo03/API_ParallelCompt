import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
from renewable_atlas.domain import GridPoint, ClimateDataSource, ClimateObservation
from .response_parser import parse_point_response
from .exceptions import NASAPowerException

DEFAULT_PARAMETERS = (
    "ALLSKY_SFC_SW_DWN,ALLSKY_SFC_SW_DNI,ALLSKY_SFC_SW_DIFF,CLRSKY_SFC_SW_DWN,"
    "ALLSKY_KT,WS10M,WS50M,WD10M,WD50M,T2M,T2M_MAX,T2M_MIN,T2MDEW,PS,RH2M,QV2M,"
    "PRECTOTCORR,CLOUD_AMT"
)

logger = logging.getLogger(__name__)


class NASAPowerDataSource(ClimateDataSource):
    def __init__(self, base_url: str, timeout: int = 30, max_retries: int = 3, start_year: int = 2000, end_year: int = 2023):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.start_year = start_year
        self.end_year = end_year

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_observations(self, point: GridPoint) -> list[ClimateObservation]:
        try:
            with httpx.Client(timeout=self.timeout, proxy=None, trust_env=False) as client:
                start_date = f"{self.start_year}0101"
                end_date = f"{self.end_year}1231"
                params = {
                    "parameters": DEFAULT_PARAMETERS,
                    "community": "RE",
                    "longitude": str(point.longitude),
                    "latitude": str(point.latitude),
                    "start": start_date,
                    "end": end_date,
                    "format": "JSON",
                }

                response = client.get(
                    "https://power.larc.nasa.gov/api/temporal/daily/point",
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
