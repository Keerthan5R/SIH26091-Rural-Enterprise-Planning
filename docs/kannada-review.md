# Kannada review checklist

**Status: the Kannada copy is machine-translated and has NOT been reviewed by a native speaker.**
This file is the worklist for that review. English and Hindi are the source of truth; the Kannada
strings are mirrors and must never change a financial figure, a verdict or a source citation.

Every `_kn` / `text_kn` / `name_kn` field falls back to English when it is missing or empty, so an
unreviewed or blank string degrades to English rather than to a blank or a Hindi leak.

## How to see it in the app

```bash
make api     # terminal 1
make web     # terminal 2, then open http://localhost:5173
```

Click **ಕನ್ನಡ** in the top bar, and print the report (browser print-to-PDF) to review the paper
sheet as well. From the CLI:

```bash
setubiz advise --village "Sulibele" --state Karnataka --savings 100000 --category dairy --income 280000 --lang kn
```

## What to review, by surface

| Surface | Where the Kannada lives | Count / notes |
|---|---|---|
| Report prose (section headings and bodies) | `backend/setubiz/narration/templates/report_sections.yaml` | Every section; keep the existing placeholders (`{{ ... }}`) intact |
| Eligibility verdict, reasons, conditions | `backend/setubiz/eligibility/rules.py`, `stacking.py`, `group.py` | Decision text only; the verdict itself is code |
| Document checks | `backend/setubiz/documents/checks.py` | All `text_kn` strings |
| Finance advisories | `backend/setubiz/finance/router.py`, `cost_templates.py`, `rightsizing.py`, `alternatives.py` | Advisories under the loan figures |
| Feasibility admonitions | `backend/setubiz/feasibility/competitors.py`, `threats.py`, `swot.py` | |
| SWOT rules | `backend/setubiz/data/{sample,real}/swot_rules.yaml` | 13 rules |
| Scheme names, notes, comparisons, stacking, SCA | `backend/setubiz/data/{sample,real}/schemes/*.yaml` | Agency name/address transcribed from the official site |
| Cost templates | `backend/setubiz/data/{sample,real}/cost_templates/*.yaml` | 8 categories; `assumptions` stay English (no `_hi` variant to mirror) |
| UI strings | `frontend/src/format.ts` (the `kn` table) | Buttons, labels, headings, empty states |
| Social-category labels | `frontend/src/format.ts` (`SOCIAL_LABELS`) | SC / safai karmachari / OBC / EBC / general |
| Inline chart and print labels | `frontend/src/components/DscrChart.tsx`, `PrintReport.tsx`, `ProvenancePanel.tsx`, `DistanceBands.tsx`, `CatchmentMap.tsx`, `ScheduleTable.tsx`, `LoanComparison.tsx`, `SeasonalityChart.tsx` | Passed through `pick(language, en, hi, kn)` |

## Terminology and decisions to confirm

- **Agency name.** "Dr. B.R. Ambedkar Development Corporation Limited" is transliterated in
  Kannada; confirm the spelling the corporation uses on its own Kannada pages.
- **Scheme names.** PMMY / PMEGP / CGTMSE / DRI / Stand-Up India / NSFDC / NSKFDC / NBCFDC are kept
  close to the English/Latin form; confirm whether the official Kannada names should replace them.
- **Finance terms.** DSCR, moratorium, margin and instalment use everyday Kannada; confirm they
  match how Karnataka bank staff and the department actually write them.
- **Digits and units.** Figures stay ASCII (1,00,000) and use the existing Indian grouping; confirm
  this reads correctly with Kannada labels.

## Known gaps

- Committed village rows carry `name_kn = null` (the Census names are Latin), so the catchment and
  village chips show the Latin name; a reviewed official Kannada village-name source is still
  needed.
- The competition layer for Karnataka is labelled "not available" (no OSM POI shard), so its
  wording should be reviewed as an error/limitation message, not as an estimate.

## Procedure

1. Read the English and Hindi line first; then judge whether the Kannada says the same thing, in
   words a beneficiary would use.
2. Fix the Kannada in place; do not touch the English or Hindi.
3. If a Kannada string is wrong enough to change meaning, mark the file and the line in this list.
4. Re-run the checks after edits:

   ```bash
   cd frontend; npm run build
   cd ..; .venv\Scripts\python.exe -m pytest backend/tests --cov=setubiz.finance --cov=setubiz.eligibility --cov=setubiz.documents --cov-fail-under=100 -q
   ```
