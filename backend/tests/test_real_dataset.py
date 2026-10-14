"""The real dataset — the one the application serves by default.

`conftest.py` pins every other test to the synthetic sample directory so its assertions stay
deterministic. This file is the exception: it asserts the committed real build actually loads,
validates and declares itself real, because that is what production and the demo run on.
"""

from __future__ import annotations

import pytest

from setubiz.config import REAL_DATA_DIR, Settings, get_settings
from setubiz.data.loader import SampleDataSource
from setubiz.facts.builder import build_facts
from setubiz.schemas import AdvisoryRequest


@pytest.fixture
def real(monkeypatch):
    monkeypatch.setenv("SETUBIZ_DATA_DIR", str(REAL_DATA_DIR))
    get_settings.cache_clear()
    yield SampleDataSource(REAL_DATA_DIR)
    get_settings.cache_clear()


def test_the_application_defaults_to_the_real_dataset():
    """If this flips back to the sample directory, every report regains the synthetic banner.

    Asserts the declared field default rather than a constructed Settings, because the suite sets
    SETUBIZ_DATA_DIR and an instance would just read that back.
    """
    assert Settings.model_fields["data_dir"].default == REAL_DATA_DIR


def test_every_village_validates_and_carries_real_geography(real):
    villages = real.all_villages()
    assert len(villages) > 10_000
    assert all(v.name and v.district and v.block for v in villages)
    assert all(0 <= v.literacy_rate <= 1 and 0 <= v.st_pct <= 1 for v in villages)
    # Jharkhand's true extent, as a guard against a broken centroid join silently shipping. Scoped
    # to Jharkhand now that the real build also serves Karnataka; the checks above stay
    # dataset-wide because they are state-independent.
    jharkhand = [v for v in villages if v.state == "Jharkhand"]
    assert jharkhand
    assert all(21.0 < v.lat < 26.0 and 83.0 < v.lon < 88.5 for v in jharkhand)


def test_population_matches_the_published_census_total(real):
    """Census 2011 puts Jharkhand's rural population at 25,055,073.

    This is the end-to-end check on the whole join chain — names, centroids, PCA and the
    exclusion of census towns. A regression in any of them moves this number.
    """
    total = sum(v.population_2011 for v in real.all_villages() if v.state == "Jharkhand")
    assert abs(total - 25_055_073) < 5_000


def test_every_source_declares_itself_real(real):
    assert real.synthetic is False
    assert all(not s for s in real.source_synthetic.values())


def test_enterprise_density_resolves_by_name_for_every_mapped_category(real):
    for category in ("all", "dairy", "kirana", "tailoring", "flour_mill"):
        density = real.block_density("Jharkhand", "Ranchi", "Ormanjhi", category)
        assert density is not None and density > 0, category
    # Deliberately unmapped: SHRIC has no livestock-rearing code, so competitors.py must fall
    # back to the observed OSM floor and say so, rather than borrow a different industry.
    assert real.block_density("Jharkhand", "Ranchi", "Ormanjhi", "poultry") is None


def test_a_report_on_real_data_carries_no_synthetic_warning(real):
    facts = build_facts(
        AdvisoryRequest(
            village_query="Ormanjhi",
            state="Jharkhand",
            savings=100000,
            business_category="dairy",
            annual_family_income=280000,
            social_category="sc",
        ),
        source=real,
    )
    assert facts.contains_synthetic_data is False
    assert not any(s.synthetic for s in facts.sources)
    assert facts.village.name == "Ormanjhi"
    assert facts.village.district == "Ranchi"


def test_an_unmapped_category_still_states_its_fallback_in_words(real):
    """A 0-0 competitor band without its caveat reads as 'no competition here'."""
    facts = build_facts(
        AdvisoryRequest(
            village_query="Ormanjhi",
            state="Jharkhand",
            savings=100000,
            business_category="poultry",
            annual_family_income=280000,
            social_category="sc",
        ),
        source=real,
    )
    assert any(n.id == "no_ec13_row" for n in facts.competitors.notes)
    assert any(w.id == "no_ec13_row" for w in facts.warnings)


def test_jharkhand_still_has_exactly_29480_villages(real):
    """Adding Karnataka must not disturb Jharkhand: the committed shard is unchanged."""
    jharkhand = [v for v in real.all_villages() if v.state == "Jharkhand"]
    assert len(jharkhand) == 29_480


def test_karnataka_real_data_loads_and_validates(real):
    karnataka = [v for v in real.all_villages() if v.state == "Karnataka"]
    assert len(karnataka) == 27_224
    assert all(v.name and v.district and v.block for v in karnataka)
    assert all(0 <= v.literacy_rate <= 1 and 0 <= v.st_pct <= 1 for v in karnataka)
    # Karnataka's true extent (11.6–18.5 N, 74.1–78.6 E), widened slightly as a sanity guard.
    assert all(11.0 < v.lat < 19.0 and 74.0 < v.lon < 79.0 for v in karnataka)


def test_a_report_on_karnataka_real_data_runs_end_to_end(real):
    facts = build_facts(
        AdvisoryRequest(
            village_query="Sulibele",
            state="Karnataka",
            savings=100000,
            business_category="dairy",
            annual_family_income=280000,
            social_category="sc",
        ),
        source=real,
    )
    assert facts.contains_synthetic_data is False
    assert not any(s.synthetic for s in facts.sources)
    assert facts.village.name == "Sulibele"
    assert facts.village.district == "Bangalore Rural"


# --- All India --------------------------------------------------------------------------

#: The Census 2011 regions the build ships. Chandigarh (04) and NCT of Delhi (07) are deliberately
#: absent: the SHRUG location module classifies every shrid there as a town, so there is no rural
#: village row to build. The total is the sum of the committed shard counts.
EXPECTED_REGIONS = 33
EXPECTED_VILLAGES = 588_691


def test_the_build_covers_every_census_2011_region_with_rural_villages(real):
    states = {s["name"]: s for s in real.list_states()}
    assert len(states) == EXPECTED_REGIONS
    assert sum(s["villages"] for s in states.values()) == EXPECTED_VILLAGES
    # The two regions with no rural village rows are absent, not zero.
    assert "Chandigarh" not in states
    assert "NCT of Delhi" not in states
    # The ampersand names survive the canonical-name round trip (SHRUG drops the "&").
    assert "Jammu & Kashmir" in states
    assert "Andaman & Nicobar Islands" in states
    assert "Dadra & Nagar Haveli" in states
    assert "Daman & Diu" in states


def test_a_wide_sample_of_new_states_loads_and_carries_real_geography(real):
    """States added beyond the Jharkhand/Karnataka references must load and validate like them."""
    sample = ("Uttar Pradesh", "Tamil Nadu", "Odisha", "Assam", "Jammu & Kashmir", "Rajasthan")
    villages = real.all_villages()
    for state in sample:
        rows = [v for v in villages if v.state == state]
        assert rows, state
        assert all(v.name and v.district and v.block for v in rows), state
        assert all(0 <= v.literacy_rate <= 1 and 0 <= v.st_pct <= 1 for v in rows), state
        # India's true extent, generous enough for Arunachal and the Andamans.
        assert all(6.0 < v.lat < 38.0 and 68.0 < v.lon < 98.0 for v in rows), state


def test_the_ampersand_states_join_to_the_economic_census(real):
    """The EC13 shard keys use the canonical PC11 name, so J&K must resolve, not silently miss.

    Before the canonical-name fix the loader joined on a title-cased SHRUG name ("Jammu Kashmir"),
    which matched no block and left those states with no density at all.
    """
    resolved = [
        v
        for v in real.all_villages()
        if v.state == "Jammu & Kashmir"
        and real.block_density(v.state, v.district, v.block, "all") is not None
    ]
    assert resolved, "no Jammu & Kashmir block resolved to an EC13 density"


def test_tiny_union_territories_serve_villages_but_have_no_estimate_layers(real):
    """Villages without an EC13/HCES denominator must still be searchable, but not fabricate one."""
    states = {s["name"]: s for s in real.list_states()}
    villages = real.all_villages()
    for name in ("Dadra & Nagar Haveli", "Daman & Diu", "Lakshadweep", "Puducherry"):
        assert name in states and states[name]["villages"] > 0, name
        assert real.layer_available(name, "villages") is True, name
        village = next(v for v in villages if v.state == name)
        # No EC13 density and no HCES demand profile were built for these (no Antyodaya households).
        assert real.block_density(name, village.district, village.block, "all") is None, name
        assert real.demand_profile(name, "dairy") is None, name
