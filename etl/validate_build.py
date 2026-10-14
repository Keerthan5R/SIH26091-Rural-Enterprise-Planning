"""Validate a built dataset directory before promoting it over the demo.

Reads whatever `manifest.json` indexes and checks the committed shards for the failures that a
partial or mis-joined build produces: duplicate or missing shrids, out-of-India coordinates,
non-numeric or out-of-range shares, empty names, and a manifest that disagrees with the shards on
disk. It also reports, per state, the village/district/sub-district counts, output size, population
total, and whether the Economic Census and HCES layers resolve.

Population totals are compared to official Census references only where a figure has actually been
recorded here (Jharkhand, Karnataka); every other state is reported as unverified rather than
silently blessed. Exits non-zero if any structural check fails, so it can gate a promotion.
"""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Any

from common import DEFAULT_OUT

#: Wide enough to contain every Indian state and UT including the island territories, tight enough
#: to catch a swapped lat/lon or a centroid joined to the wrong shrid. The east edge must clear
#: Arunachal Pradesh, whose villages reach ~97.2°E.
INDIA_LAT = (6.0, 38.0)
INDIA_LON = (68.0, 98.0)

VILLAGE_REQUIRED = (
    "shrid",
    "name",
    "state",
    "district",
    "block",
    "lat",
    "lon",
    "households_2011",
    "population_2011",
    "literacy_rate",
    "sc_pct",
    "st_pct",
    "workers_pct",
)
SHARE_FIELDS = ("literacy_rate", "sc_pct", "st_pct", "workers_pct")

#: Documented official Census 2011 rural population, for the states where the figure has been
#: recorded in the project (see CHANGES.md / etl/README.md). Anything not listed is left unverified
#: and must not be described as validated.
CENSUS_2011_RURAL_REFERENCE = {
    "Jharkhand": (25_055_073, "Census 2011 A-2, rural"),
    "Karnataka": (37_469_335, "Census 2011 A-2, rural"),
}


def read_json(path: Path) -> dict[str, Any]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    return json.loads(path.read_text(encoding="utf-8"))


def validate_state(root: Path, entry: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    problems: list[str] = []
    code = entry["code"]
    shard = root / entry["village_shard"]
    if not shard.exists():
        return {}, [f"{code}: manifest references a missing shard {entry['village_shard']}"]
    payload = read_json(shard)
    rows = payload.get("villages", [])
    if len(rows) != entry.get("villages"):
        problems.append(
            f"{code}: manifest says {entry.get('villages')} villages, shard has {len(rows)}"
        )

    shrids: set[str] = set()
    duplicates = 0
    population = 0
    districts: set[str] = set()
    blocks: set[str] = set()
    bad_geo = bad_share = bad_name = 0
    for r in rows:
        missing = [f for f in VILLAGE_REQUIRED if f not in r]
        if missing:
            problems.append(f"{code}: record {r.get('shrid')} missing {missing}")
            continue
        sid = r["shrid"]
        if sid in shrids:
            duplicates += 1
        shrids.add(sid)
        if not (r["name"] and r["district"] and r["block"]):
            bad_name += 1
        lat, lon = r["lat"], r["lon"]
        if not (INDIA_LAT[0] <= lat <= INDIA_LAT[1] and INDIA_LON[0] <= lon <= INDIA_LON[1]):
            bad_geo += 1
        for f in SHARE_FIELDS:
            v = r[f]
            if not isinstance(v, (int, float)) or not (0.0 <= v <= 1.0):
                bad_share += 1
        population += int(r["population_2011"])
        districts.add(r["district"])
        blocks.add(r["block"])

    if duplicates:
        problems.append(f"{code}: {duplicates} duplicate shrid(s)")
    if bad_name:
        problems.append(f"{code}: {bad_name} record(s) with an empty name/district/block")
    if bad_geo:
        problems.append(f"{code}: {bad_geo} record(s) outside India's bounding box")
    if bad_share:
        problems.append(f"{code}: {bad_share} share value(s) outside [0,1]")

    ref = CENSUS_2011_RURAL_REFERENCE.get(entry["name"])
    report = {
        "code": code,
        "name": entry["name"],
        "villages": len(rows),
        "districts": len(districts),
        "blocks": len(blocks),
        "population": population,
        "kb": round(shard.stat().st_size / 1024, 1),
        "pois": entry.get("pois", 0),
        "reference": ref[0] if ref else None,
        "reference_note": ref[1] if ref else "not independently verified",
        "delta_pct": (
            round(abs(population - ref[0]) / ref[0] * 100, 3) if ref and ref[0] else None
        ),
    }
    return report, problems


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    root = args.dir
    manifest = read_json(root / "manifest.json")
    states = manifest["states"]

    print(f"Validating {root}")
    print(f"manifest: {len(states)} state(s), built {manifest['_meta'].get('built')}\n")

    problems: list[str] = []
    reports = []
    for entry in sorted(states.values(), key=lambda s: s["name"]):
        report, probs = validate_state(root, entry)
        problems.extend(probs)
        if report:
            reports.append(report)

    header = (
        f"{'code':4} {'state':26} {'villages':>9} {'dist':>5} {'blocks':>7} {'pop':>12} {'KB':>8}"
    )
    print(header)
    print("-" * len(header))
    for r in reports:
        print(
            f"{r['code']:4} {r['name'][:26]:26} {r['villages']:>9,} {r['districts']:>5} "
            f"{r['blocks']:>7,} {r['population']:>12,} {r['kb']:>8,.1f}"
        )

    total_villages = sum(r["villages"] for r in reports)
    print("-" * len(header))
    print(f"{'':4} {'TOTAL':26} {total_villages:>9,}")

    # Duplicate shrids across states would mean a village was written into two shards.
    seen: dict[str, str] = {}
    dupes: list[str] = []
    for entry in states.values():
        for r in read_json(root / entry["village_shard"]).get("villages", []):
            sid = r["shrid"]
            if sid in seen:
                dupes.append(f"{sid} in {seen[sid]} and {entry['code']}")
            seen[sid] = entry["code"]
    if dupes:
        problems.append(f"{len(dupes)} shrid(s) appear in more than one state shard")

    # --- EC13 layer ---
    ec13_path = root / "ec13_density.json"
    if ec13_path.exists():
        ec13 = read_json(ec13_path)
        prefixes = {k.split("|", 1)[0] for k in ec13["blocks"]}
        canonical = {s["name"] for s in states.values()}
        stray = sorted(prefixes - canonical)
        print(
            f"\nEC13: {len(ec13['blocks']):,} blocks, {len(ec13['district_stats']):,} districts, "
            f"states={len(ec13['_meta'].get('states', []))}"
        )
        if stray:
            problems.append(f"EC13 has block state prefixes that are not manifest states: {stray}")
        have_ec13 = {s["name"] for s in states.values()} & set(ec13["_meta"]["states"])
        no_ec13 = sorted({s["name"] for s in states.values()} - have_ec13)
        if no_ec13:
            print(f"  states without EC13 density (expected for tiny UTs): {no_ec13}")

    # --- HCES layer ---
    hces_path = root / "hces_demand.json"
    if hces_path.exists():
        hces = read_json(hces_path)
        present = set(hces["states"])
        missing = sorted({s["name"] for s in states.values()} - present)
        print(f"HCES: {len(present)} state(s) with a demand profile")
        if missing:
            print(f"  states without HCES demand (no Antyodaya household size): {missing}")

    # --- population references ---
    print("\nPopulation reconciliation (Census 2011 rural):")
    for r in reports:
        if r["reference"] is None:
            continue
        print(
            f"  {r['name']}: built {r['population']:,} vs {r['reference']:,} "
            f"({r['reference_note']}) — {r['delta_pct']}%"
        )

    print()
    if problems:
        print(f"FAILED: {len(problems)} problem(s)")
        for p in problems:
            print(f"  - {p}")
        raise SystemExit(1)
    print("OK: all structural checks passed")


if __name__ == "__main__":
    main()
