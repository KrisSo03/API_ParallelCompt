from renewable_atlas.infrastructure.nasa_power.client import NASAPowerDataSource
from renewable_atlas.infrastructure.nasa_power.response_parser import parse_point_response
from renewable_atlas.domain import GridPoint


def test_parse_point_response_reads_current_api_shape():
    payload = {
        "properties": {
            "parameter": {
                "ALLSKY_SFC_SW_DWN": {"20200101": 5.2, "20200102": 4.8},
                "WS50M": {"20200101": 2.1, "20200102": 2.5},
                "WS10M": {"20200101": 2.3, "20200102": 2.7},
            }
        }
    }

    observations = parse_point_response(payload)

    assert len(observations) == 2
    assert observations[0].sw_dwn == 5.2
    assert observations[0].ws_50m == 2.1
    assert observations[0].ws_100m == 2.3
    assert observations[0].dni is None


def test_nasa_power_data_source_uses_current_endpoint(monkeypatch):
    class DummyResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    class DummyClient:
        def __init__(self, timeout, proxy=None, trust_env=False):
            self.timeout = timeout
            self.proxy = proxy
            self.trust_env = trust_env

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url, params):
            assert url == "https://power.larc.nasa.gov/api/temporal/daily/point"
            assert params["community"] == "RE"
            assert params["format"] == "JSON"
            return DummyResponse({"properties": {"parameter": {"ALLSKY_SFC_SW_DWN": {"20200101": 1.0}, "WS50M": {"20200101": 1.1}, "WS10M": {"20200101": 1.2}}}})

    monkeypatch.setattr("renewable_atlas.infrastructure.nasa_power.client.httpx.Client", DummyClient)

    source = NASAPowerDataSource(base_url="https://power.larc.nasa.gov/api/")
    point = GridPoint(latitude=13.7, longitude=-92.2, country="Guatemala")
    observations = source.fetch_observations(point)

    assert len(observations) == 1
    assert observations[0].sw_dwn == 1.0
