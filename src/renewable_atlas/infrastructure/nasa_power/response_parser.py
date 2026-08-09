from datetime import datetime

from renewable_atlas.domain import ClimateObservation

VARIABLE_FIELD_MAP = {
    "ALLSKY_SFC_SW_DWN": "sw_dwn",
    "ALLSKY_SFC_SW_DNI": "dni",
    "ALLSKY_SFC_SW_DIFF": "sw_diff",
    "CLRSKY_SFC_SW_DWN": "clr_sky_sw_dwn",
    "ALLSKY_KT": "allsky_kt",
    "WS10M": "ws_10m",
    "WS50M": "ws_50m",
    "WD10M": "wd_10m",
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
WIND_SHEAR_EXPONENT = 1 / 7


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

            ws_50m = values.get("ws_50m")
            # POWER provides WS10M and WS50M, not WS100M. Keep both measured
            # heights and derive the existing 100 m dashboard field explicitly.
            ws_100m = (
                float(ws_50m) * (100 / 50) ** WIND_SHEAR_EXPONENT if ws_50m is not None else None
            )
            observation = ClimateObservation(date=date, ws_100m=ws_100m, **values)
            observations.append(observation)

        except (ValueError, IndexError, TypeError):
            continue

    return observations
