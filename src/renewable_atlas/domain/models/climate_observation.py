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

    PLAUSIBLE_RANGES: ClassVar[dict] = {
        "sw_dwn": (0, 400),
        "dni": (0, 900),
        "ws_50m": (0, 25),
        "ws_100m": (0, 30),
    }

    def is_complete(self) -> bool:
        return all(v is not None for v in [self.sw_dwn, self.dni, self.ws_50m, self.ws_100m])
