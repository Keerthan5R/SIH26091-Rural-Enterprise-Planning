# Kannada rollout — progress log

Records each Kannada task in order: files touched, commit, validation, and limitations.
Kannada strings are machine-translated and need native-speaker review (see `docs/kannada-review.md`, T27).

| Task | Scope | Commit | Validation | Limitations |
| --- | --- | --- | --- | --- |
| T01 | `Language` enum + `Advisory` (`schemas.py`) | `90b1f3a` | ruff, pytest 358, coverage 100%, build PASS | none |
| T02 (T03 merged) | report templates (`report_sections.yaml`) + `template_narrator.py` | `f58e186` | ruff, pytest 358, coverage 100%, build PASS | scheme/village names fall back until their `_kn` fields exist |
| T04 | `facts/builder.py` — `verbatim_text()` carries Kannada | `ec7916b` | ruff, pytest 358, coverage 100%, build PASS | reads `_kn` defensively; gaps close as other tasks add fields |
| T05 | document checks (`documents/schemas.py`, `documents/checks.py`) | `143b49c` | ruff, pytest 358, coverage 1227/0 100%, build PASS | none |
| T06 | finance engine (`finance/router.py`, `cost_templates.py`, `rightsizing.py`, `alternatives.py`) | `9b647af` | ruff, pytest 358, coverage 1232/0 100%, build PASS | none |
| T07 | feasibility (`feasibility/competitors.py`, `threats.py`, `swot.py`, `finance/cost_templates.py` `display_name()`) | `9326c72` | ruff, pytest 358, coverage 1232/0 100%, build PASS | none |
| T08 | eligibility (`eligibility/rules.py`, `stacking.py`, `group.py`) | `5365229` | ruff check + format --check, pytest 358, coverage 1257/0 100%, build PASS | data-driven `_kn` fields (corporation/document/comparison/stacking/`income_ceiling_note_kn`/shg `unconfirmed_kn`) stay English until T09–T10 populate the YAML |
| T09 | sample scheme datasets (`data/sample/schemes/*.yaml`) | `1df71fd` | YAML parse, ruff, pytest 358, coverage 1257/0 100%, build PASS | `logics:` (unparsed) and `handoffs:` (not rendered) left English; KA SCA `name_hi` already held Kannada text (unchanged) |
| T10 | real scheme datasets (`data/real/schemes/*.yaml`) | `47116b8` | YAML parse, ruff, pytest 358, coverage 1257/0 100%, build PASS | real schemes were byte-identical to sample pre-T09, so the same Kannada carries over; same `logics:`/`handoffs:` gap |
| T11 | SWOT rules (`swot_rules.yaml`, sample & real) | `14dfe85` | YAML parse, `text_kn` placeholders verified identical to `text_en`, ruff, pytest 358, coverage 1257/0 100%, build PASS | none |
| T12 | sample cost templates (all 8 categories) | `8e22092` | additions-only vs prior blob (amounts/scaling/source/assumptions byte-identical), ruff, pytest 358, coverage 1257/0 100%, build PASS | `assumptions` stay English (no `_hi` variant exists to mirror) |
| T13 | real cost templates (all 8 categories) | `465e71a` | additions-only vs prior blob, ruff, pytest 358, coverage 1257/0 100%, build PASS | real templates were byte-identical to sample pre-T12; same `assumptions` gap |
| T14 | `data/loader.py` + `narration/template_narrator.py` + `report_sections.yaml` + `cli.py` | `6666003` | ruff check + format --check, pytest 358, coverage 1257/0 100%, build PASS; KN narration grounded 44/44 with no literal `None` | committed village rows have `name_kn = null` (Census names are Latin), so the report falls back to English; Kannada village names need a real source (see review doc) |
| T16 | `matching/village_matcher.py` + `schemas.py` + `tests/test_matcher.py` | `4322d88` | ruff check + format --check, pytest 365, coverage 1257/0 100%, build PASS; Kannada query returns confirmable candidates | transliteration is approximate, so a Kannada query may rank a soundalike above the intended village (the UI asks the user to confirm) |
| T17+T18 | `frontend/src/types.ts` + `format.ts` (+ prop widening in 7 components) | `fd119f3` | build PASS (tsc + verify-ux4g) | merged: widening `Language` without the `kn` table breaks the build; components still fall back to English until T21-T23 |
| T19 | `components/layout/TopBar.tsx` + `urlState.ts` | `8a976c7` | build PASS | none |
| T20 | `package.json` + `main.tsx` + `app.css` (`@fontsource/noto-sans-kannada`) | `6131f37` | build PASS (Kannada woff2 emitted) | new npm dependency, approved by the user; :lang(kn) font-token binding is the one documented exception in app.css |
| T21 | `pages/Report.tsx` + `Ask.tsx` + `Documents.tsx` + `format.ts` (`tenureUnit`) + `api.ts` (`DocumentCheck.text_kn`) | `fdc95b7` | build PASS, pytest 365 | none |
| T22 | `components/PrintHeader.tsx` + `PrintReport.tsx` + `format.ts` (`yes`/`no`) | `474455b` | build PASS, pytest 365 | print logic A/B copy translated inline via `pick` |
| T23 | `CatchmentMap`, `DistanceBands`, `VillagePicker`, `OutOfScope`, `DscrChart`, `ProvenancePanel` | `87d0342` | build PASS, pytest 365 | Kannada chart labels and catchments tip; no data change |
| T24 | `LoanComparison`, `ScheduleTable`, `SeasonalityChart` | `d67d946` | build PASS, pytest 365 | none |
| T25 | `tests/test_validator.py` + `tests/test_content_style.py` | `d1425dd` | pytest 379, coverage 1257/0 100%, ruff check + format --check | grounding and em-dash checks now include Kannada |
| T26 (merged into T25) | template-narrator Kannada assertion (`tests/test_content_style.py`) | `d1425dd` | pytest 379, coverage 1257/0 100% | folded into T25 so the suite stayed green in one commit |
| T15 (skipped) | no separate Kannada narrator lane | — | documented in `docs/PRD-COVERAGE.md` | the deterministic template narrator is already the default lane; the cloud and local-LLM lanes paraphrase it, so adding `kn` to it was the whole change |
| T27 | `docs/kannada-review.md` (native-speaker review checklist) | `e5802ac` | docs only | machine translations still need a native-speaker pass |
| T28 | progress-log and `CHANGES.md` rows for the docs tasks | `e5802ac` | docs only | none |
| T29 | `README.md` + `docs/PRD-COVERAGE.md` Kannada updates (379 tests, Kannada matching, self-hosted font, three-language narrator) | `e5802ac` | docs only; pytest 379, build PASS | none |

Notes:
- Coverage gate: `--cov=setubiz.finance --cov=setubiz.eligibility --cov=setubiz.documents --cov-fail-under=100`.
- All changes are additive (`_kn`/`text_kn`/`name_kn` fields and Kannada strings); English and Hindi wording is unchanged.
- Every task was committed separately; nothing is pushed.
