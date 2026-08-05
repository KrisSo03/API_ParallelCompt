from renewable_atlas.application.services import ClusterInterpretationService
from renewable_atlas.domain import ClusterProfile


def make_profile(cluster_id, sw_dwn, dni, ws_50m, ws_100m, size=10):
    return ClusterProfile(
        cluster_id=cluster_id,
        label=f"Cluster {cluster_id}",
        description="",
        size=size,
        centroid={
            "sw_dwn_mean": sw_dwn,
            "dni_mean": dni,
            "ws_50m_mean": ws_50m,
            "ws_100m_mean": ws_100m,
        },
    )


def test_interpret_labels_highest_solar_and_lowest_wind_as_solar_dominant():
    profiles = [
        make_profile(0, sw_dwn=300, dni=280, ws_50m=2, ws_100m=3),   # solar alto, viento bajo
        make_profile(1, sw_dwn=100, dni=90, ws_50m=8, ws_100m=9),    # solar bajo, viento alto
    ]
    service = ClusterInterpretationService()

    result = service.interpret(profiles)

    solar_cluster = next(p for p in result if p.cluster_id == 0)
    wind_cluster = next(p for p in result if p.cluster_id == 1)

    assert solar_cluster.label == "Solar-dominant"
    assert wind_cluster.label == "Wind-dominant"


def test_interpret_labels_four_quadrants_correctly():
    profiles = [
        make_profile(0, sw_dwn=300, dni=280, ws_50m=8, ws_100m=9),   # ambos altos -> hibrido
        make_profile(1, sw_dwn=300, dni=280, ws_50m=2, ws_100m=3),   # solar alto, viento bajo
        make_profile(2, sw_dwn=100, dni=90, ws_50m=8, ws_100m=9),    # solar bajo, viento alto
        make_profile(3, sw_dwn=100, dni=90, ws_50m=2, ws_100m=3),    # ambos bajos -> bajo potencial
    ]
    service = ClusterInterpretationService()

    result = service.interpret(profiles)
    labels = {p.cluster_id: p.label for p in result}

    assert labels[0] == "Hybrid-high"
    assert labels[1] == "Solar-dominant"
    assert labels[2] == "Wind-dominant"
    assert labels[3] == "Lower-resource"


def test_interpret_uses_only_four_expected_labels():
    profiles = [
        make_profile(0, sw_dwn=250, dni=200, ws_50m=5, ws_100m=6),
        make_profile(1, sw_dwn=150, dni=140, ws_50m=6, ws_100m=7),
        make_profile(2, sw_dwn=200, dni=190, ws_50m=4, ws_100m=5),
    ]
    service = ClusterInterpretationService()

    result = service.interpret(profiles)

    allowed_labels = {"Solar-dominant", "Wind-dominant", "Hybrid-high", "Lower-resource"}
    assert all(p.label in allowed_labels for p in result)


def test_interpret_handles_missing_variables_gracefully():
    # dni_mean falta en todos los clusters (columna no disponible)
    profiles = [
        ClusterProfile(
            cluster_id=0, label="", description="", size=5,
            centroid={"sw_dwn_mean": 300, "ws_50m_mean": 2, "ws_100m_mean": 3},
        ),
        ClusterProfile(
            cluster_id=1, label="", description="", size=5,
            centroid={"sw_dwn_mean": 100, "ws_50m_mean": 8, "ws_100m_mean": 9},
        ),
    ]
    service = ClusterInterpretationService()

    result = service.interpret(profiles)

    assert result[0].label == "Solar-dominant"
    assert result[1].label == "Wind-dominant"


def test_interpret_single_cluster_does_not_crash():
    profiles = [make_profile(0, sw_dwn=200, dni=180, ws_50m=5, ws_100m=6)]
    service = ClusterInterpretationService()

    result = service.interpret(profiles)

    assert len(result) == 1
    assert result[0].label in {"Solar-dominant", "Wind-dominant", "Hybrid-high", "Lower-resource"}
    assert result[0].solar_percentile == 0.5
    assert result[0].wind_percentile == 0.5


def test_interpret_sets_confidence_between_0_and_1():
    profiles = [
        make_profile(0, sw_dwn=300, dni=280, ws_50m=1, ws_100m=1),
        make_profile(1, sw_dwn=290, dni=270, ws_50m=1.5, ws_100m=1.5),
        make_profile(2, sw_dwn=100, dni=90, ws_50m=9, ws_100m=10),
    ]
    service = ClusterInterpretationService()

    result = service.interpret(profiles)

    for profile in result:
        assert 0.0 <= profile.confidence <= 1.0


def test_interpret_empty_profiles_returns_empty():
    service = ClusterInterpretationService()
    assert service.interpret([]) == []



def test_interpret_mentions_dominant_country_when_breakdown_available():
    profile = make_profile(0, sw_dwn=300, dni=280, ws_50m=2, ws_100m=3)
    profile.country_breakdown = {
        "CR": {"count": 7, "percentage": 0.7},
        "PA": {"count": 3, "percentage": 0.3},
    }
    other = make_profile(1, sw_dwn=100, dni=90, ws_50m=8, ws_100m=9)

    service = ClusterInterpretationService()
    result = service.interpret([profile, other])

    interpreted = next(p for p in result if p.cluster_id == 0)
    assert "CR" in interpreted.description
    assert "70%" in interpreted.description


def test_interpret_description_without_country_breakdown_does_not_crash():
    profiles = [
        make_profile(0, sw_dwn=300, dni=280, ws_50m=2, ws_100m=3),
        make_profile(1, sw_dwn=100, dni=90, ws_50m=8, ws_100m=9),
    ]
    service = ClusterInterpretationService()

    result = service.interpret(profiles)

    assert all("Pais dominante" not in p.description for p in result)