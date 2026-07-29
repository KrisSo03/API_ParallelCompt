from datetime import datetime
from renewable_atlas.domain import ClimateObservation

VARIABLE_FIELD_MAP = {
    "SW_DWN": "sw_dwn",
    "DNI": "dni",
    "WS50M": "ws_50m",
    "WS100M": "ws_100m",
}

FILL_VALUE = -999


def parse_point_response(data: dict) -> list[ClimateObservation]:
    observations = []
    properties = data.get("properties", {})
    daily_data = properties.get("daily", {})

    if not daily_data:
        return observations

    dates = daily_data.get("YEAR", [])
    sw_dwn_values = daily_data.get("SW_DWN", [])
    dni_values = daily_data.get("DNI", [])
    ws_50m_values = daily_data.get("WS50M", [])
    ws_100m_values = daily_data.get("WS100M", [])

    for i, (year, month, day) in enumerate(zip(
        daily_data.get("YEAR", []),
        daily_data.get("MO", []),
        daily_data.get("DY", []),
    )):
        try:
            date = datetime(year, month, day).date()

            sw_dwn = sw_dwn_values[i] if i < len(sw_dwn_values) else None
            dni = dni_values[i] if i < len(dni_values) else None
            ws_50m = ws_50m_values[i] if i < len(ws_50m_values) else None
            ws_100m = ws_100m_values[i] if i < len(ws_100m_values) else None

            sw_dwn = None if sw_dwn == FILL_VALUE else sw_dwn
            dni = None if dni == FILL_VALUE else dni
            ws_50m = None if ws_50m == FILL_VALUE else ws_50m
            ws_100m = None if ws_100m == FILL_VALUE else ws_100m

            observation = ClimateObservation(
                date=date,
                sw_dwn=sw_dwn,
                dni=dni,
                ws_50m=ws_50m,
                ws_100m=ws_100m,
            )
            observations.append(observation)

        except (ValueError, IndexError):
            continue

    return observations
