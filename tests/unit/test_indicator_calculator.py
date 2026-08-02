import pandas as pd

from renewable_atlas.application.services.indicator_service import IndicatorCalculator


def test_indicator_calculator_computes_normalized_scores():
    df = pd.DataFrame(
        {
            "sw_dwn": [100.0, 200.0],
            "dni": [50.0, 80.0],
            "ws_50m": [4.0, 8.0],
            "ws_100m": [6.0, 12.0],
        }
    )

    calculator = IndicatorCalculator()
    result = calculator.calculate(1, 10.0, -84.0, "Costa Rica", df)

    assert result.sw_dwn_mean == 150.0
    assert result.dni_mean == 65.0
    assert result.ws_100m_mean == 9.0
    assert result.solar_score > 0.0
    assert result.wind_score > 0.0
    assert result.hybrid_score > 0.0
