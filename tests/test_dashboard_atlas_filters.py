import pandas as pd
import pytest

from dashboard.atlas_filters import point_label, select_featured_points


def _points() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "country": ["A", "A", "A", "B", "B", "B"],
            "point_id": [3, 2, 1, 6, 5, 4],
            "solar_score": [0.9, 0.9, 0.2, 0.8, 0.7, 0.1],
        }
    )


def test_featured_points_keeps_top_n_for_each_country() -> None:
    result = select_featured_points(_points(), "solar_score", 2)

    assert result.groupby("country").size().to_dict() == {"A": 2, "B": 2}
    assert result["point_id"].tolist() == [2, 3, 6, 5]


def test_featured_points_rejects_invalid_arguments() -> None:
    with pytest.raises(ValueError, match="Unknown atlas metric"):
        select_featured_points(_points(), "missing", 5)
    with pytest.raises(ValueError, match="at least 1"):
        select_featured_points(_points(), "solar_score", 0)


def test_point_label_is_shared_user_facing_identifier() -> None:
    assert point_label(pd.Series({"country": "Costa Rica", "point_id": 7})) == (
        "Costa Rica · Punto 7"
    )
