"""Tests for the ETL builders' pure logic.

The ETL is dev-time code that streams multi-gigabyte extracts, so these tests deliberately exercise
only the pieces that can be driven from small, in-memory inputs: the Census 2011 state inventory,
the per-state shard partition/merge that makes batched EC13 builds safe, and the tolerance for a
missing or empty SHRIC description table. The full builds are validated separately by
`test_real_dataset.py` against whatever shards are committed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# The ETL scripts import each other by bare module name (`from common import ...`) because they are
# run from inside etl/. Put that directory on the path so the tests can import them too.
ETL = Path(__file__).resolve().parents[2] / "etl"
if str(ETL) not in sys.path:
    sys.path.insert(0, str(ETL))

import build_ec13_density as ec13  # noqa: E402
import build_villages as villages  # noqa: E402
import common  # noqa: E402


def test_pc11_inventory_is_the_census_2011_set():
    assert len(common.PC11_STATES) == 35
    assert common.PC11_STATES["29"] == ("Karnataka", "KA")
    assert common.PC11_STATES["20"] == ("Jharkhand", "JH")
    # Telangana (created 2014) has no PC11 id; its villages ship under Andhra Pradesh (28).
    assert "36" not in common.PC11_STATES
    assert all(len(code) == 2 for _, code in common.PC11_STATES.values())


def test_resolve_state_accepts_id_code_and_name():
    assert common.resolve_state("20") == "20"
    assert common.resolve_state("JH") == "20"
    assert common.resolve_state("Jharkhand") == "20"
    with pytest.raises(SystemExit):
        common.resolve_state("Atlantis")


def test_code_of_name_round_trips_every_pc11_state():
    for _, (name, code) in common.PC11_STATES.items():
        assert common.code_of_name(name) == code


def test_code_of_name_falls_back_instead_of_raising():
    assert common.code_of_name("Some New UT") == "SomeNewUt"


def test_partition_by_state_splits_on_the_first_pipe_field():
    blocks = {"A|B|C": {"all": 1.0}, "A|B|D": {"all": 2.0}, "X|Y|Z": {"all": 3.0}}
    stats = {"A|B": {"all": {"mean": 1, "std": 0, "n_blocks": 2}}}
    parts = ec13.partition_by_state(blocks, stats)
    assert set(parts) == {"A", "X"}
    assert set(parts["A"]["blocks"]) == {"A|B|C", "A|B|D"}
    assert parts["X"]["district_stats"] == {}


def test_a_later_batch_never_drops_an_earlier_states_blocks(tmp_path):
    shard_dir = tmp_path / "ec13_density"
    ec13.write_json(
        shard_dir / "JH.json",
        {
            "_meta": {"state": "Jharkhand"},
            "blocks": {"Jharkhand|Ranchi|Ormanjhi": {"all": 10.0}},
            "district_stats": {},
        },
    )
    # A second batch for a different state. The merge must still see Jharkhand.
    ec13.write_json(
        shard_dir / "KA.json",
        {
            "_meta": {"state": "Karnataka"},
            "blocks": {"Karnataka|Belgaum|Chikodi": {"all": 5.0}},
            "district_stats": {},
        },
    )
    merged = ec13.merge_shards(shard_dir)
    assert merged["states"] == ["Jharkhand", "Karnataka"]
    assert "Jharkhand|Ranchi|Ormanjhi" in merged["blocks"]
    assert "Karnataka|Belgaum|Chikodi" in merged["blocks"]


def test_sharding_a_legacy_single_file_keeps_every_state(tmp_path):
    legacy = tmp_path / "ec13_density.json"
    legacy.write_text(
        json.dumps(
            {
                "blocks": {
                    "Jharkhand|Ranchi|Ormanjhi": {"all": 1.0},
                    "Karnataka|Belgaum|Chikodi": {"all": 2.0},
                },
                "district_stats": {},
            }
        ),
        encoding="utf-8",
    )
    count = ec13.seed_shards_from_legacy(tmp_path / "ec13_density", legacy)
    assert count == 2
    merged = ec13.merge_shards(tmp_path / "ec13_density")
    assert merged["states"] == ["Jharkhand", "Karnataka"]


def test_the_category_split_survives_an_empty_description_table(monkeypatch, tmp_path):
    empty = tmp_path / "shric_descriptions.csv"
    empty.write_text("shric,shric_desc\n", encoding="utf-8")
    monkeypatch.setattr(ec13, "SHRIC_DESC", empty)
    mapping, why = ec13.load_mapping()
    assert "dairy" in mapping and "flour_mill" in mapping
    assert why["dairy"]


def test_share_is_clamped_and_guards_a_zero_denominator():
    assert villages.share(1, 0) == 0.0
    assert villages.share(None, 10) == 0.0
    assert villages.share(5, 10) == 0.5
    assert villages.share(20, 10) == 1.0
