# Dataset ETL

Turns the multi-gigabyte extracts in `datasets/` (gitignored) into the small, committed files
under `backend/setubiz/data/real/`.

Nothing here is imported by the application. The seam is the on-disk schema, which is identical to
the one `SampleDataSource` already reads — so switching the app to real data is one env var:

```bash
SETUBIZ_DATA_DIR=backend/setubiz/data/real make api
```

## Status

| Output | State | Source |
|---|---|---|
| `villages/<ST>.json.gz` | **real, all 33 regions** | Census 2011 PCA + SHRUG names/spatial stats + Mission Antyodaya amenities; one shard per state (588,691 villages) |
| `ec13_density/<ST>.json` | **real, per-state shard** | Economic Census 2013 via SHRUG `ec13_shrid.csv`, split by SHRIC code, households from Mission Antyodaya |
| `ec13_density.json` | **real, merged** | Union of every `ec13_density/<ST>.json` shard; written by the same script so batched runs never drop a region |
| `hces_demand.json` | **real** | HCES 2023-24 Fact Sheet, Statements 4 & 7 and Figure 1R (29 states) |
| `pois/<ST>.json.gz` | **real** | OpenStreetMap via Overpass; only Jharkhand ships so far |
| `arrivals.json` | live prices only | data.gov.in; needs a personal key and a portal history export |
| `manifest.json` | **real** | index of the committed shards, read by the loader at startup |
| `schemes/`, `cost_templates/`, `swot_rules.yaml` | real already | copied from `data/sample/`, unchanged |

## Commands

```bash
cd etl
python3 build_villages.py    --states all   # or --states JH / BR OD WB; prints what is missing
python3 build_ec13_density.py --states all  # writes per-state shards + the merged file
python3 build_hces_demand.py                # all states in one file
python3 fetch_pois.py        --states JH --pause 3    # ~2.5 min per category, cached
python3 fetch_arrivals.py    --states JH [--history agmarknet_export.csv]
python3 build_manifest.py                   # run last; indexes whatever shards exist

# validate a build (structural checks + population reconciliation) before promoting:
python3 validate_build.py [--dir <build-dir>]   # defaults to backend/setubiz/data/real
```

`--states` accepts PC11 ids (`20`), two-letter codes (`JH`) or names (`Jharkhand`); `all` does
every region. Overpass responses are cached under `etl/.cache/`, so re-runs are free.

## Honesty constraints encoded here

These are deliberate and should survive refactors:

* **All 35 Census 2011 regions are attempted; 33 have rural villages.** Chandigarh and Delhi write
  no shard: the SHRUG location module classifies every shrid there as a census town, with no rural
  village row to build from.
* **Canonical state names.** SHRUG lowercases names and drops `&`, so `.title()` cannot restore
  "Jammu & Kashmir" or "Daman & Diu". Every shard key uses the canonical PC11 name from
  `state_name(sid)`, so the loader's join on `Village.state` matches instead of silently missing
  those regions. `code_of_name()` maps a name back to a code with a slug fallback that never raises.
* **Per-state shards, merged additively.** `build_ec13_density.py` writes `ec13_density/<ST>.json`
  per state and merges them into `ec13_density.json`, so running one batch (e.g. only the two
  original states) never drops another region's blocks. `validate_build.py` checks the merge.
* **Some union territories carry villages but no estimates.** Dadra & Nagar Haveli, Daman & Diu,
  Lakshadweep and Puducherry have rural villages but no Mission Antyodaya household rows, so they
  get no EC13 density and no HCES demand profile. Village search works; a full advisory returns a
  clear absence rather than a fabricated estimate.
* **Census 2011 boundary vintage.** The region list is Census 2011, not the present map: Telangana
  (carved out in 2014) ships under Andhra Pradesh, and Census-2011 Jammu & Kashmir includes Ladakh.
  Recorded as `CENSUS_2011_BOUNDARY_NOTE` in `common.py` so a reader cannot mistake it for a bug.

* **EC13 has no per-industry establishment counts.** Only `ec13_count_all` plus 90
  `ec13_emp_shric_*` *employment* columns. A per-category count can therefore only be apportioned
  as `count_all x (emp_shric_cat / emp_all)`, and the emitted `method_note` says so. The category
  split is gated on the SHRUG "SHRIC Industry Code" module and stays off until it is downloaded —
  guessing which of 90 codes means "dairy" is not acceptable.
* **EC13 covers rural and urban; Mission Antyodaya is rural-only.** Mixing them puts a town's
  establishments over a handful of rural households. The numerator is restricted to the rural
  shrid set from `ec13r_shrid_key.csv`. Before this fix the worst Jharkhand block read 5,912
  enterprises per 1,000 households; after it, 773, with a median of 49.
* **Population comes from PC11, not Antyodaya.** Antyodaya's counts are ~2019; feeding them into
  fields named `*_2011` would double-count growth already applied by `intercensal_growth`.
  Antyodaya supplies amenities only.
* **`addressable_share` in `hces_demand.json` is an assumption** and ships its own rationale
  string. `share_of_mpce` and `cv` are not assumptions — the first is published, the second is
  computed from the published rural MPCE distribution.
* **Census towns are excluded.** `shrid_loc_names.csv` distinguishes `town_name` from
  `village_name`; the 228 Jharkhand census towns are dropped. Mission Antyodaya has no urban rows,
  so a town would carry fabricated amenity flags — a town of 22,000 defaulting to
  `has_bank: False` — and `ec13_density.json` is likewise built on the rural universe. Validation:
  the resulting population totals **25,054,425 against the published Jharkhand rural Census 2011
  figure of 25,055,073**, a difference of 648 (0.003%). The `_meta` counters
  (`census_towns_excluded`, `without_amenity_row`) are per state, so each shard describes its own
  exclusions rather than stamping an all-India total onto every state.
* **The SHRIC category mapping is a judgement, and is written down.** `etl/shric_categories.json`
  maps each business category onto SHRUG industry codes and records *why* for each; every code is
  validated against `shric_descriptions.csv` at build time, so a typo is an error rather than a
  column of silent zeros. `dairy` (code 7) and `flour_mill` (code 8) are exact matches.
* **`poultry` is deliberately unmapped.** SHRIC has no livestock-rearing code. The nearest, 5
  'Processing of meat', is a different business — a backyard unit rears birds and sells eggs, it
  does not run a processing establishment — and its real competitors are other backyard units the
  Economic Census never registers. So the category is left out, `competitors.py` falls back to the
  OSM floor, and the report says so in words.
* **Rural OSM coverage is very sparse.** All of Jharkhand has 120 mapped POIs across the six
  categories: 87 kirana, 23 marketplaces, 7 dairy, 2 poultry, 1 tailor, 0 flour mills. This is
  why `feasibility/competitors.py` treats an observed count as a floor and never as a census.
* **`dist_to_town_km` is measured, not estimated.** SHRUG's `shrid2_spatial_stats.csv` publishes
  `tdist_50`, the km distance to the nearest town of 50,000+ — the smallest settlement that
  reliably has a bank branch, a wholesale market and transport links. The same file publishes the
  authoritative centroid, which is why the 874 MB shrid GeoPackage is not needed.
* **The AGMARKNET API is a daily snapshot, not a history.** The seasonality index needs 12 months,
  which must be exported from the portal and passed with `--history`. Without it the file carries
  no `series` and `threats.assess` drops the seasonality threat rather than inventing one.
