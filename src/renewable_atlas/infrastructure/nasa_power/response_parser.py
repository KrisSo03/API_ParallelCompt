from datetime import datetime
from renewable_atlas.domain import ClimateObservation

VARIABLE_FIELD_MAP = {
    "ALLSKY_SFC_SW_DWN": "sw_dwn",
    "ALLSKY_SFC_SW_DNI": "dni",
    "ALLSKY_SFC_SW_DIFF": "sw_diff",
    "CLRSKY_SFC_SW_DWN": "clr_sky_sw_dwn",
    "ALLSKY_KT": "allsky_kt",
    "WS10M": "ws_100m",
    "WS50M": "ws_50m",
    "WD10M": "wd_100m",
    "WD50M": "wd_50m",
    "T2M": "t2m",
    "T2M_MAX": "t2m_max",
    "T2M_MIN": "t2m_min",
    "T2MDEW": "t2mdew",
    "PS": "ps",
    "RH2M": "rh2m",
    "QV2M": "qv2m",
    "PRECTOTCORR": "prectotcorr",
    "CLOUD_AMT": "cloud_amt",
}

FILL_VALUE = -999


def parse_point_response(data: dict) -> list[ClimateObservation]:
    observations = []
    properties = data.get("properties", {})
    parameter_data = properties.get("parameter", {})

    if not parameter_data:
        return observations

    dates = sorted(parameter_data.get("ALLSKY_SFC_SW_DWN", {}).keys())
    if not dates:
        return observations

    for date_key in dates:
        try:
            year = int(date_key[:4])
            month = int(date_key[4:6])
            day = int(date_key[6:8])
            date = datetime(year, month, day).date()

            values = {}
            for variable, field_name in VARIABLE_FIELD_MAP.items():
                raw_value = parameter_data.get(variable, {}).get(date_key)
                values[field_name] = None if raw_value == FILL_VALUE else raw_value

            observation = ClimateObservation(
                date=date,
                sw_dwn=values.get("sw_dwn"),
                dni=values.get("dni"),
                ws_50m=values.get("ws_50m"),
                ws_100m=values.get("ws_100m"),
            )
            observations.append(observation)

        except (ValueError, IndexError, TypeError):
            continue

    return observations
