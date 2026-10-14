"""Phonetic village matching — demo-critical, so tested against realistic ASR noise."""

from __future__ import annotations

import pytest

from setubiz.data.loader import SampleDataSource, Village
from setubiz.matching.village_matcher import indic_soundex, match_villages, transliterate


@pytest.fixture
def source():
    return SampleDataSource()


@pytest.mark.parametrize(
    ("devanagari", "expected"),
    [("ओरमांझी", "ormanjhi"), ("रातू", "ratu"), ("कांके", "kanke"), ("बेड़ो", "bero")],
)
def test_transliteration_of_devanagari_village_names(devanagari, expected):
    assert transliterate(devanagari) == expected


def test_transliteration_normalizes_latin_input():
    assert transliterate("  Ormanjhi-123 ") == "ormanjhi"
    assert transliterate("") == ""


@pytest.mark.parametrize(
    ("kannada", "expected"),
    [("ಓರಮಾಂಝಿ", "oormanjhi"), ("ರಾತೂ", "ratuu"), ("ಕಾಂಕೆ", "kanke"), ("ಬೇರೋ", "beeroo")],
)
def test_transliteration_of_kannada_village_names(kannada, expected):
    assert transliterate(kannada) == expected


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("Ormanjhi", "Ormanji"),  # the aspirate an ASR usually drops
        ("Kanke", "Kankay"),
        ("Bero", "Beroo"),
        ("Ratu", "Raatu"),
        ("Chanho", "Chano"),
    ],
)
def test_aspirates_and_long_vowels_do_not_change_the_phonetic_code(a, b):
    assert indic_soundex(a) == indic_soundex(b)


def test_soundex_separates_genuinely_different_names():
    assert indic_soundex("Ratu") != indic_soundex("Kanke")
    assert indic_soundex("") == ""


@pytest.mark.parametrize("spoken", ["Ormanji", "ormanjhi", "Aurmanjhi", "ओरमांझी", "ORMANJI"])
def test_the_intended_village_is_the_top_match(spoken, source):
    matches = match_villages(spoken, source, state="Jharkhand")
    assert matches, spoken
    assert matches[0].name == "Ormanjhi"
    assert matches[0].reason


@pytest.mark.parametrize("spoken", ["ಓರಮಾಂಝಿ", "ಓರಮಾಂಜಿ"])
def test_a_kannada_script_query_returns_confirmable_candidates(spoken, source):
    matches = match_villages(spoken, source, state="Jharkhand", limit=5)
    assert matches
    assert "Ormanjhi" in {m.name for m in matches}
    assert all(m.reason for m in matches)


def test_a_village_kannada_name_is_scored_alongside_latin_and_hindi():
    village = Village(
        shrid="x",
        name="Kanke",
        name_hi="कांके",
        name_kn="ಕಾಂಕೆ",
        state="Jharkhand",
        district="Ranchi",
        block="Kanke",
        lat=23.45,
        lon=85.33,
        households_2011=1,
        population_2011=1,
        literacy_rate=0.6,
        sc_pct=0.1,
        st_pct=0.0,
        workers_pct=0.6,
        has_bank=True,
        has_pucca_road=True,
        has_power=True,
        dist_to_town_km=5.0,
    )

    class _OneVillage:
        def all_villages(self):
            return (village,)

    matches = match_villages("ಕಾಂಕೆ", _OneVillage(), limit=1)
    assert matches and matches[0].name == "Kanke"


def test_results_are_ranked_capped_and_confirmable(source):
    matches = match_villages("Nagri", source, limit=3)
    assert 1 <= len(matches) <= 3
    assert [m.score for m in matches] == sorted((m.score for m in matches), reverse=True)
    assert all(0 <= m.score <= 1 for m in matches)
    assert all(m.shrid and m.block and m.district for m in matches)


def test_a_gps_prior_pulls_the_nearby_candidate_up(source):
    near_kanke = (23.4283, 85.3216)
    with_prior = match_villages("Nagri", source, near=near_kanke, limit=5)
    without = match_villages("Nagri", source, limit=5)
    assert with_prior[0].score > without[0].score
    assert "nearby" in with_prior[0].reason


def test_state_and_district_filters_narrow_the_pool(source):
    assert match_villages("Ratu", source, state="Kerala") == ()
    assert match_villages("Ratu", source, district="Ranchi")
    assert match_villages("Ratu", source, district="Bokaro") == ()


def test_empty_and_hopeless_queries_return_nothing(source):
    assert match_villages("   ", source) == ()
    assert match_villages("zzzzqqqq", source) == ()
