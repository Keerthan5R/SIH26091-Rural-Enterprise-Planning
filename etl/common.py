"""Shared helpers for the dataset ETL.

These scripts are dev-time only: they read the multi-gigabyte extracts in `datasets/` (gitignored)
and emit the small, sharded, committed files under `backend/setubiz/data/real/`. Nothing here is
imported by the application — the seam is the on-disk schema, which is identical to the one
`SampleDataSource` already reads.
"""

from __future__ import annotations

import csv
import gzip
import json
import sys
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASETS = REPO_ROOT / "datasets"
DEFAULT_OUT = REPO_ROOT / "backend" / "setubiz" / "data" / "real"
CACHE = Path(__file__).resolve().parent / ".cache"

#: Census 2011 (PC11) state codes. `shrid2` is "11-<state>-<district>-<subdistrict>-<village>", so
#: the second field is the join key for every state-level operation, including shard naming.
#:
#: This is the Census 2011 inventory, not a claim about India's current boundaries. Three later
#: administrative changes are deliberately *not* reflected, because the only data source (SHRUG
#: v2.2) ships Census 2011 geometry and identifiers, and remapping it would be inventing data:
#:
#: 1. Telangana (current State 36) was carved out of Andhra Pradesh in 2014 and has no PC11 id.
#:    Its villages therefore arrive under id 28 ("Andhra Pradesh") and a report for one will read
#:    its state as Andhra Pradesh — honest but coarse.
#: 2. Jammu & Kashmir was reorganised in 2019 into the UTs of Jammu & Kashmir and Ladakh. PC11 id
#:    01 ("Jammu & Kashmir") still includes the districts that are now Ladakh.
#: 3. Dadra & Nagar Haveli and Daman & Diu were merged into one UT in 2020. PC11 keeps them apart as
#:    ids 26 and 25.
#:
#: The per-state shards are named and labelled with these Census 2011 state names for that reason.
CENSUS_2011_BOUNDARY_NOTE = (
    "Census 2011 regions (35). India's current map differs: Telangana (2014) has no PC11 id and "
    "its villages appear under Andhra Pradesh (28); Jammu & Kashmir (01) still includes Ladakh; "
    "Dadra & Nagar Haveli (26) and Daman & Diu (25) are still separate. SHRUG v2.2 ships PC11 "
    "boundaries, so these are preserved rather than guessed at."
)
PC11_STATES: dict[str, tuple[str, str]] = {
    "01": ("Jammu & Kashmir", "JK"),
    "02": ("Himachal Pradesh", "HP"),
    "03": ("Punjab", "PB"),
    "04": ("Chandigarh", "CH"),
    "05": ("Uttarakhand", "UK"),
    "06": ("Haryana", "HR"),
    "07": ("NCT of Delhi", "DL"),
    "08": ("Rajasthan", "RJ"),
    "09": ("Uttar Pradesh", "UP"),
    "10": ("Bihar", "BR"),
    "11": ("Sikkim", "SK"),
    "12": ("Arunachal Pradesh", "AR"),
    "13": ("Nagaland", "NL"),
    "14": ("Manipur", "MN"),
    "15": ("Mizoram", "MZ"),
    "16": ("Tripura", "TR"),
    "17": ("Meghalaya", "ML"),
    "18": ("Assam", "AS"),
    "19": ("West Bengal", "WB"),
    "20": ("Jharkhand", "JH"),
    "21": ("Odisha", "OD"),
    "22": ("Chhattisgarh", "CG"),
    "23": ("Madhya Pradesh", "MP"),
    "24": ("Gujarat", "GJ"),
    "25": ("Daman & Diu", "DD"),
    "26": ("Dadra & Nagar Haveli", "DN"),
    "27": ("Maharashtra", "MH"),
    "28": ("Andhra Pradesh", "AP"),
    "29": ("Karnataka", "KA"),
    "30": ("Goa", "GA"),
    "31": ("Lakshadweep", "LD"),
    "32": ("Kerala", "KL"),
    "33": ("Tamil Nadu", "TN"),
    "34": ("Puducherry", "PY"),
    "35": ("Andaman & Nicobar Islands", "AN"),
}

_CODE_TO_ID = {code: sid for sid, (_, code) in PC11_STATES.items()}
_NAME_TO_ID = {name.lower(): sid for sid, (name, _) in PC11_STATES.items()}
_NAME_TO_CODE = {name: code for name, code in PC11_STATES.values()}


def state_id_of(shrid: str) -> str | None:
    """'11-20-346-02495-347134' -> '20'. None when the shrid is malformed."""
    parts = shrid.split("-")
    return parts[1] if len(parts) >= 2 and parts[1] in PC11_STATES else None


def resolve_state(token: str) -> str:
    """Accept '20', 'JH' or 'Jharkhand' and return the PC11 state id."""
    t = token.strip()
    if t in PC11_STATES:
        return t
    if t.upper() in _CODE_TO_ID:
        return _CODE_TO_ID[t.upper()]
    if t.lower() in _NAME_TO_ID:
        return _NAME_TO_ID[t.lower()]
    raise SystemExit(f"unknown state {token!r}; use a PC11 id, a 2-letter code or a state name")


def state_name(state_id: str) -> str:
    return PC11_STATES[state_id][0]


def state_code(state_id: str) -> str:
    return PC11_STATES[state_id][1]


def code_of_name(name: str) -> str:
    """The two-letter PC11 code for a state name, for naming per-state shards.

    Falls back to a filesystem-safe slug rather than raising: block/district keys are built from
    SHRUG's own state names, and a shard must never be dropped because a name did not match the
    table exactly.
    """
    if name in _NAME_TO_CODE:
        return _NAME_TO_CODE[name]
    slug = "".join(c for c in name.title() if c.isalnum())
    return slug[:12] or "UNKNOWN"


def read_csv(path: Path, columns: list[str] | None = None) -> Iterator[dict[str, str]]:
    """Stream a CSV. `columns` restricts each row to the named fields, which matters a great deal
    on the 139-column EC13 and 160-column Antyodaya files."""
    if not path.exists():
        raise SystemExit(f"missing input: {path}\nDownload it into datasets/ and re-run.")
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if columns:
            missing = [c for c in columns if c not in (reader.fieldnames or [])]
            if missing:
                raise SystemExit(f"{path.name} is missing expected columns: {missing}")
            for row in reader:
                yield {c: row[c] for c in columns}
        else:
            yield from reader


def num(value: str | None, default: float | None = None) -> float | None:
    """SHRUG writes floats, empty strings and 'NA' interchangeably. One parser for all of them."""
    if value is None:
        return default
    v = value.strip()
    if not v or v.upper() in {"NA", "N/A", "NULL", "."}:
        return default
    try:
        return float(v)
    except ValueError:
        return default


def flag(value: str | None) -> bool:
    """Antyodaya booleans arrive as '1.0' / '0.0' / ''."""
    return (num(value, 0.0) or 0.0) >= 0.5


def meta(source: str, note: str, **extra: Any) -> dict[str, Any]:
    """Every emitted file carries where it came from and when.

    `synthetic: False` is the load-bearing part: the loader reads it back to decide whether a
    report may be cited. Files without the key are assumed synthetic, so the committed sample
    dataset keeps its warning without needing to be touched.
    """
    return {"source": source, "note": note, "built": date.today().isoformat(),
            "synthetic": False, **extra}


def write_json(path: Path, payload: dict[str, Any], *, compress: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    target = path.with_suffix(path.suffix + ".gz") if compress else path
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if compress:
        # mtime=0 so rebuilding identical data produces an identical file and git stays quiet.
        with gzip.GzipFile(target, "wb", compresslevel=9, mtime=0) as fh:
            fh.write(blob)
    else:
        target.write_bytes(blob)
    # Builds are run into a scratch output directory before promotion, which can live outside the
    # repo; relative_to() would raise there, so fall back to the absolute path for the log line.
    try:
        shown = target.relative_to(REPO_ROOT)
    except ValueError:
        shown = target
    print(f"  wrote {shown}  ({target.stat().st_size / 1024:.0f} KB)")


def progress(label: str, n: int, every: int = 100_000) -> None:
    if n % every == 0:
        print(f"  {label}: {n:,} rows", file=sys.stderr)
