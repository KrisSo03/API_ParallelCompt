import pandas as pd

from dashboard.metrics import (
    country_comparison,
    enrich_indicators,
    featured_profile_id,
    filter_indicators,
    overview_metrics,
    performance_summary,
    profile_scores,
)


def _indicators():
    return pd.DataFrame(
        {
            "point_id": [0, 1, 2],
            "country": ["Costa Rica", "Panama", "Costa Rica"],
            "cluster_id": [0, 1, 0],
            "solar_score": [0.8, 0.3, 0.6],
            "wind_score": [0.4, 0.9, 0.5],
            "hybrid_score": [0.6, 0.7, 0.55],
        }
    )


def test_enriches_indicators_with_profile_labels():
    profiles = [
        {"cluster_id": 0, "label": "Solar-dominant"},
        {"cluster_id": 1, "label": "Wind-dominant"},
    ]

    enriched = enrich_indicators(_indicators(), profiles)

    assert enriched["cluster_label"].tolist() == [
        "Solar-dominant",
        "Wind-dominant",
        "Solar-dominant",
    ]


def test_filters_by_country_and_cluster():
    filtered = filter_indicators(_indicators(), countries=["Costa Rica"], cluster_ids=[0])

    assert filtered["point_id"].tolist() == [0, 2]


def test_computes_overview_for_selected_metric():
    result = overview_metrics(_indicators(), "hybrid_score")

    assert result.points == 3
    assert result.countries == 2
    assert result.clusters == 2
    assert result.best_country == "Panama"
    assert result.average_score == (0.6 + 0.7 + 0.55) / 3


def test_selects_strongest_visible_cluster_and_its_scores():
    indicators = _indicators()

    cluster_id = featured_profile_id(indicators, "wind_score")
    scores = profile_scores(indicators, cluster_id)

    assert cluster_id == 1
    assert scores["wind_score"] == 0.9


def test_compares_country_score_averages():
    result = country_comparison(_indicators(), ["Costa Rica", "Panama"])

    costa_rica = result[result["country"] == "Costa Rica"].iloc[0]
    assert costa_rica["solar_score"] == 0.7
    assert costa_rica["hybrid_score"] == 0.575


def test_summarizes_performance_and_derives_speedup():
    summary = pd.DataFrame(
        {
            "status": ["success", "success", "success", "success"],
            "workers": [1, 1, 2, 2],
            "elapsed_seconds": [20.0, 22.0, 11.0, 13.0],
        }
    )

    result = performance_summary(summary)

    assert result["workers"].tolist() == [1, 2]
    assert result["tiempo_mediano"].tolist() == [21.0, 12.0]
    assert result.iloc[1]["speedup"] == 21.0 / 12.0
    assert result.iloc[1]["eficiencia"] == (21.0 / 12.0) / 2
