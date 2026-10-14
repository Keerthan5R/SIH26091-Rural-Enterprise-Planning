"""A state whose optional layer was never built must say so, never read absence as zero.

Karnataka ships villages but no OpenStreetMap POI shard. The competitor estimator must label the
layer unavailable instead of reporting "no competition"; Jharkhand's floor-and-cite behaviour, and
the flat synthetic layout, must be untouched.
"""

from __future__ import annotations

import pytest

from setubiz.config import REAL_DATA_DIR, get_settings
from setubiz.data.loader import SampleDataSource
from setubiz.feasibility import competitors, market_reach


@pytest.fixture
def real(monkeypatch):
    monkeypatch.setenv("SETUBIZ_DATA_DIR", str(REAL_DATA_DIR))
    get_settings.cache_clear()
    yield SampleDataSource(REAL_DATA_DIR)
    get_settings.cache_clear()


def test_layer_availability_reflects_the_committed_shards(real):
    assert real.layer_available("Jharkhand", "villages") is True
    assert real.layer_available("Jharkhand", "pois") is True
    assert real.layer_available("Karnataka", "villages") is True
    assert real.layer_available("Karnataka", "pois") is False
    # Accepted by either the full state name or its two-letter code.
    assert real.layer_available("JH", "pois") is True
    assert real.layer_available("KA", "pois") is False
    # A state that is not in the build at all is unavailable, not an error.
    assert real.layer_available("Odisha", "pois") is False


def test_layer_availability_rejects_an_unknown_layer(real):
    with pytest.raises(KeyError, match="unknown layer"):
        real.layer_available("Karnataka", "roads")


def test_flat_sample_layout_has_every_layer_available():
    # The synthetic layout has no manifest and ships one combined POI file.
    assert SampleDataSource().layer_available("Anywhere", "pois") is True
    assert SampleDataSource().layer_available("Anywhere", "villages") is True


def test_competitor_estimate_labels_a_missing_poi_layer_as_unavailable(real):
    village = next(v for v in real.all_villages() if v.state == "Karnataka")
    reach = market_reach.compute(village, real, radius_km=10.0)
    est = competitors.Ec13ZScoreEstimator().estimate(village, reach, "dairy", real)

    note = next((n for n in est.notes if n.id == "osm_layer_unavailable"), None)
    assert note is not None
    assert note.text_en and note.text_hi
    # The band must not claim an observed OSM floor or cite OSM as a source.
    assert "openstreetmap" not in est.band.sources
    assert "floored by observed" not in est.band.method
    assert "economic_census_2013" in est.band.sources


def test_jharkhand_still_uses_the_observed_floor_and_cites_osm(real):
    village = next(v for v in real.all_villages() if v.state == "Jharkhand")
    reach = market_reach.compute(village, real, radius_km=10.0)
    est = competitors.Ec13ZScoreEstimator().estimate(village, reach, "dairy", real)

    assert not any(n.id == "osm_layer_unavailable" for n in est.notes)
    assert "openstreetmap" in est.band.sources
    assert "floored by observed" in est.band.method
