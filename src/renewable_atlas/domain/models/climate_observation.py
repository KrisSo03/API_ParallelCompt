import math
from dataclasses import dataclass
from datetime import date
from typing import ClassVar


@dataclass
class ClimateObservation:
    date: date
    sw_dwn: float | None
    dni: float | None
    ws_50m: float | None
    ws_100m: float | None
    ws_10m: float | None = None
    sw_diff: float | None = None
    clr_sky_sw_dwn: float | None = None
    allsky_kt: float | None = None
    wd_100m: float | None = None
    wd_50m: float | None = None
    wd_10m: float | None = None
    t2m: float | None = None
    t2m_max: float | None = None
    t2m_min: float | None = None
    t2mdew: float | None = None
    ps: float | None = None
    rh2m: float | None = None
    qv2m: float | None = None
    prectotcorr: float | None = None
    cloud_amt: float | None = None

    PLAUSIBLE_RANGES: ClassVar[dict] = {
        "sw_dwn": (0, 400),
        "dni": (0, 900),
        "ws_50m": (0, 25),
        "ws_100m": (0, 30),
        "ws_10m": (0, 30),
        "sw_diff": (0, 400),
        "clr_sky_sw_dwn": (0, 400),
        "allsky_kt": (0, 1.5),
        "wd_10m": (0, 360),
        "wd_50m": (0, 360),
        "wd_100m": (0, 360),
        "t2m": (-100, 70),
        "t2m_max": (-100, 70),
        "t2m_min": (-100, 70),
        "t2mdew": (-100, 70),
        "ps": (50, 120),
        "rh2m": (0, 100),
        "qv2m": (0, 100),
        "prectotcorr": (0, 1000),
        "cloud_amt": (0, 100),
    }

    def __post_init__(self) -> None:
        for field_name, (min_value, max_value) in self.PLAUSIBLE_RANGES.items():
            value = getattr(self, field_name)

            if value is None:
                continue

            try:
                value = float(value)
            except (TypeError, ValueError):
                setattr(self, field_name, None)
                continue

            if math.isnan(value) or math.isinf(value):
                setattr(self, field_name, None)
                continue

            if value < min_value or value > max_value:
                setattr(self, field_name, None)
            else:
                setattr(self, field_name, value)

    def is_complete(self) -> bool:
        return all(v is not None for v in [self.sw_dwn, self.dni, self.ws_50m, self.ws_100m])
