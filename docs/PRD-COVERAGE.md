# PLAN.md coverage

What of the master plan is actually built, section by section. Written to be read by the team
before the **20 Sep 2026** idea gate, and to be the honest answer when a judge asks "how much of
this is real".

Status as of the working tree. Legend: **Built** runs today and is tested · **Partial** runs but
falls short of the plan's spec · **Not built** does not exist.

Headline: **the deterministic decision layer is complete, the pipeline runs end to end, and the
village/density/consumption data is now real and national — 588,691 Census 2011 rural villages
across 33 regions, Economic Census 2013 density and HCES 2023-24 demand for 29 states.** **No ML
model is trained.** That split is deliberate, it matches PLAN.md §2's layering rule, and it is the
thing to say out loud rather than paper over.

---

## §2 The pipeline

| Stage | Status | Notes |
|---|---|---|
| Voice in (village, savings, idea, language) | **Partial** | Browser Web Speech API (`hi-IN`, `kn-IN`), degrades to typing. `frontend/src/components/MicButton.tsx` |
| Silero VAD | **Not built** | |
| ASR (IndicConformer / IndicWhisper, INT8) | **Not built** | Browser ASR stands in |
| Intent + slot classifier (Model ③) | **Not built** | The form collects slots explicitly instead |
| Phonetic village matcher | **Built** | Devanagari and Kannada transliteration + Indic Soundex + rapidfuzz + GPS prior, top-3 for confirmation. `matching/village_matcher.py` |
| shrid lookup, villages within radius | **Built** | Haversine over committed rows, behind the `DataSource` protocol. `geo.py`, `data/loader.py` |
| PostGIS | **Not built** | Swapping it in touches only `data/loader.py` |
| OSRM isochrone | **Not built** | PLAN.md marks it a stretch |
| Data: SHRUG / OSM / HCES / AGMARKNET | **Partial** | Real and national for villages, EC13 density and HCES demand; OSM POIs Jharkhand-only; AGMARKNET still snapshot-only. See §6 |
| NABARD cost templates | **Built** | 5 templates, line items follow published norms. `data/sample/cost_templates/` |
| Estimation ①②④ | **Partial** | v0 deterministic estimators, every output a band. See §3 |
| Decision: finance + rules | **Built** | 100% test coverage |
| Scheme stacking | **Not built** | Comparison cards exist; a stacking graph does not |
| Locked `facts.json` | **Built** | `facts/builder.py`, with a `provenance` map and a `numeric_index` |
| RAG (BGE-M3 → pgvector → reranker) | **Not built** | Scheme text is structured YAML, not retrieved chunks |
| Narration LLM | **Partial** | Cloud lane (off by default) and the new local lane. See §3 |
| GBNF grammar constraint | **Built** | On the local lane. `narration/local_narrator.py:sections_grammar` |
| Numeric grounding + catch rate | **Built** | `narration/validator.py`, rate served at `/api/v1/metrics` |
| On-screen report with citations | **Built** | Per-section source footers plus the provenance panel |
| TTS read-aloud | **Not built** | |
| PDF bank handout | **Partial** | Print stylesheet, browser print-to-PDF. WeasyPrint needs GTK natives |
| Ministry dashboard | **Not built** | |

---

## §3 Models

| # | Model | Status | What exists instead |
|---|---|---|---|
| ① | Competitor density (LightGBM) ★ | **Not built** | The plan's own v0 fallback: EC13 block-density z-score × households, floored by observed OSM POIs, emitted as a ±35% band. `LightgbmDensityEstimator` is registered and raises `NotImplementedError`, so enabling it is a config change. The baseline it must beat (raw OSM count) is reported alongside every estimate |
| ② | Local demand (HCES, Fay-Herriot) | **Not built** | State mean ± coefficient of variation as a band. The baseline (state average applied uniformly) is the band's own point estimate, and the report says so |
| ③ | Intent + slot classifier | **Not built** | No conversational parsing at all; slots come from form fields |
| ④ | Price seasonality (SARIMA/Prophet) | **Not built** | A deterministic arrivals index (CV, peak/trough, peak-to-trough ratio) that feeds the Threats section and the seasonality chart. The plan calls ④ a stretch and the *chart* the deliverable; the chart exists |

**No model is trained, so no model reports a metric against its baseline.** That is the single
biggest gap between the plan and the build, and it is blocked on data, not on code: every estimator
sits behind a protocol with a registry, so a trained model is a swap rather than a rewrite.

### Pretrained stack

| Component | Status |
|---|---|
| Silero VAD | **Not built** |
| IndicConformer / IndicWhisper ASR (INT8) | **Not built** |
| Indic-TTS / Piper | **Not built** |
| BGE-M3 embeddings, bge-reranker-v2-m3 | **Not built** |
| Narration LLM, cloud primary | **Built**, off by default. Anthropic adapter with structured outputs, `narration/llm_narrator.py`. PLAN.md named Gemini/Groq; the adapter is one class either way |
| **Llama 3.1 8B Instruct Q4_K_M local fallback** | **Built**, weights not shipped. See below |

### The local 8B lane, in detail

`narration/local_narrator.py`, added because it is the offline/CSC story and the answer to "what if
the network dies at the venue".

- Runs llama.cpp through `llama-cpp-python`, installed via the optional `[local]` extra.
- **GBNF grammar** generated per report from the section ids. Each entry is pinned to its own id in
  order, so the model cannot reorder, drop or invent a section; only body text is free. This is
  PLAN.md §3's anti-hallucination layer 1 implemented literally rather than by analogy.
- Shares `ParaphraseNarrator` with the cloud lane: it paraphrases the deterministic template
  report, never computes, and every generation goes through numeric grounding with retries.
- The narrator ladder is cloud, then local, then template. `/api/v1/metrics` reports which lane
  would serve the next request and whether weights are present.

**Unverified:** the weights are a ~4.7 GB download this repo does not fetch, so generation quality
on the real model has never been observed. What is tested is the grammar, the availability gate,
the retry loop, the rejection of an ungrounded paraphrase, and the fallback. Turning the lane on
without weights provably cannot degrade the demo. To try it:

```bash
pip install -e ".[local]"
# fetch a Meta-Llama-3.1-8B-Instruct Q4_K_M GGUF, then:
export SETUBIZ_LOCAL_LLM_ENABLED=1
export SETUBIZ_LOCAL_LLM_MODEL_PATH=~/models/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf
```

### Deliberately not ML, as the plan requires

EMI and loan maths, eligibility verdicts, stress tests: all auditable code, 100% covered.
**No business-failure classifier**, because no labelled dataset of failed rural micro-enterprises
exists. The report volunteers this before it is asked, in the "What happens in a bad year" section.

### Anti-hallucination, all three layers

| Layer | Status |
|---|---|
| 1. Grammar-constrained decoding | **Built** on both lanes: GBNF locally, `output_config.format` on the cloud |
| 2. Numeric grounding | **Built**. Tolerance derives from how precisely a figure is written, not a blanket percentage |
| 3. Verdict fidelity | **Built**. Verdicts are copied from the facts object; the model only paraphrases prose |
| Catch rate logged and presented | **Built**, at `/api/v1/metrics` and in the report footer |

**Known limit, worth volunteering:** layer 2 catches *invented* numbers, not *misattributed* ones.
A figure lifted from row 14 of the repayment schedule and captioned as something else is grounded
and passes. Layer 3 is what guards that, and only for verdicts.

---

## §4 Module 1, the six PS parameters

| Parameter | Status | Notes |
|---|---|---|
| Market Reach | **Built** | Σ population in radius × district intercensal factor, income-segmented. Mandis counted; haats and bus routes not |
| Opportunity Analysis | **Built** | Block activity-density z-scores vs district mean |
| SWOT | **Built** | 13-rule YAML library over computed metrics, trilingual (en/hi/kn), each line citing its sources. Never an LLM |
| Threats | **Partial** | Arrivals seasonality, monsoon dependency, single-buyer and road-access flags. No flood/drought layers (IMD, NDMA) |
| Competitor Mapping | **Partial** | Band with a confidence badge and the observed-count floor. No MapLibre POI heatmap |
| Product Market Value | **Partial** | Mandi price band × purchasing power. No single "recommended price point" |
| Report pipeline with provenance footers | **Built** | |
| Offline template-only fallback | **Built** | The default lane, not a degraded mode |

---

## §5 Module 2, financial structuring

**Everything in this section is built, and it is the strongest part of the repo.**

| Item | Status |
|---|---|
| Router: margin → project cost → loan, Logic A/B, caps ₹1.25 L / ₹45 L | **Built** |
| Rates 6.5% / 8.0%, tenures 3 yr / 7 yr, quarterly instalments | **Built** |
| Moratorium 3 mo / 6 mo, 12 mo for plantation and construction | **Built** |
| Edge cases, including margins outside the envelope with referrals | **Built** |
| Quarterly amortization, both moratorium treatments always shown | **Built** |
| Golden test vectors | **Built**, with a correction: PLAN.md's vector A of ₹12,471 is wrong; it is **₹12,501.34**. See the README |
| DSCR right-sizing, threshold 1.5, stress at −15% / −30% | **Built**, plus a stress floor so the recommendation must survive a bad year |
| Binding-constraint reporting | **Built**, beyond the plan: the UI names *why* the number is what it is |
| Category routing, income ceilings, verdicts, documents, SCA, PM-DAKSH | **Built** |
| Comparison schemes (PMMY, PMEGP, CGTMSE, DRI, Stand-Up India) | **Partial**: data and API are there, no UI toggle |

---

## §6 Data

**Real and national.** `data/real/` holds Census 2011 PCA + SHRUG v2.2 names, centroids and
spatial stats + Mission Antyodaya amenities for **588,691 rural villages across 33 regions** (28
states + 5 UTs), Economic Census 2013 density (5,534 blocks, 605 districts, 29 states) and HCES
2023-24 consumption (29 states). `data/sample/` remains as a synthetic fallback and declares itself
so. The honest limits: **Chandigarh and Delhi** have no rural village rows in the source (no
shard);
**Dadra & Nagar Haveli, Daman & Diu, Lakshadweep and Puducherry** serve village search only (no
EC13/HCES, so a full advisory returns a clear 404); OSM POIs are **Jharkhand-only**; and the
region list is the **Census 2011 boundary vintage** (Telangana ships under Andhra Pradesh, J&K
includes Ladakh).

| Source | Status |
|---|---|
| SHRUG v2.2 (villages, spatial stats) | **Ingested**, all 33 regions |
| Census 2011 PCA | **Ingested**, per village |
| Mission Antyodaya amenities | **Ingested**, 521,069 villages have an amenity row |
| Economic Census 2013 | **Ingested**, 29 states (SHRIC-split density) |
| OSM Overpass POIs | **Ingested for Jharkhand only**; every other state's POI layer reads unavailable |
| HCES 2023-24 (cat. 237) | **Ingested** as published shares → 29 state demand profiles |
| AGMARKNET live API | **Still a daily snapshot**, no 12-month history |
| Udyam granularity check | **Not done**, and it is what gates Model ① |
| NABARD cost templates | Authored from published norms |
| Scheme parameters | **Real and cited** |
| Ranchi ground-truth shop-count validation | **Not done**. PLAN.md §9 calls this the credibility claim no one else has |

---

## §7 Stack

Built: FastAPI · React + Tailwind PWA · Docker Compose (`make demo`) · a Typer CLI the plan did not
ask for. Not built: PostgreSQL/PostGIS/pgvector · MapLibre · Celery · WeasyPrint · scikit-learn and
LightGBM · ONNX Runtime. llama.cpp is now wired but unexercised.

Charts are hand-rolled SVG against a CVD-validated palette rather than a charting library, which
keeps the bundle at 60 KB gzipped JS and 6 KB CSS. Fonts are self-hosted per subset, so the app
still needs no network. That matters on a rural connection.

---

## §1 Product modes

| Mode | Status |
|---|---|
| (a) Self-serve voice PWA | **Partial**: the PWA is built and bilingual; the voice layer is a browser stub |
| (b) Assisted VLE / CSC operator mode | **Not built** |
| (c) Ministry policy dashboard | **Not built** |

## §9 Differentiators

1. Right-sized vs max loan, with the red column: **built**, and it is the demo.
2. Speaks NSFDC/SCA natively, including the Jan-2026 ₹5 L ceiling: **built**.
3. Every number computed and cited, grammar-constrained, catch rate, provenance panel: **built**.
4. Competitor-density ML with honest baselines and a Ranchi ground-truth check: **not built**.
5. Assisted VLE mode and ministry dashboard: **not built**.
6. Voice-first vernacular with an offline lane: **partial**, offline lane built.

---

## Kannada (Karnataka adaptation)

The Karnataka rollout (tracked in `docs/kannada-progress.md`) adds Kannada as a third language
alongside English and Hindi, without changing English or Hindi wording:

- **Report and UI.** The language switcher, report prose, eligibility verdict and reasons, SWOT
  and threats, documents, finance advisories, cost-template names, the printed sheet and every
  chart label render in Kannada (`en`/`hi`/`kn`). Kannada falls back to English field-by-field
  when a translation is missing.
- **Village matching.** The phonetic matcher accepts Kannada script as well as Latin and
  Devanagari (`matching/village_matcher.py`).
- **Voice.** The mic button asks the browser for `kn-IN` when Kannada is selected.
- **Font.** Noto Sans Kannada is self-hosted and bound to `:lang(kn)`, so Indian-language faces
  load only for the script on screen.
- **Grounding.** The numeric-grounding and em-dash content checks cover Kannada, and a test
  asserts a Kannada narrative is written in Kannada script. The verdict decision remains
  deterministic code; the narrator only explains, in Kannada like the other two languages. There
  is no separate Kannada narrative lane to build: the template narrator is the default lane (the
  cloud and local-LLM lanes paraphrase it), and adding `kn` to it is the whole change.
- **Caveat for review.** The Kannada copy is machine-translated and is listed for a
  native-speaker pass in `docs/kannada-review.md`.

---

## What would move the needle before 20 Sep

1. **Verify Udyam granularity** (half a day, blocks Model ①). Until this is answered, the flagship
   model cannot be designed, let alone trained. PLAN.md §6 already calls it the first task.
2. **Ingest real SHRUG v2.2 rows for Ranchi** (one day). Turns every number in the demo from
   "shaped like the truth" into the truth, and removes the synthetic-data banner.
3. **Train Model ① even crudely, and report it against the raw-OSM baseline** (two days after 1
   and 2). A trained model with an honest metric beats a better model with none.
4. **Ranchi ground-truth shop count** (one day, mostly legwork). The claim no competing team can
   make.
5. **Assisted VLE mode** (one day). It is mostly a different landing screen over the same pipeline,
   and it is the deployment story the ministry actually cares about.

Deliberately *not* on this list: ASR/TTS, RAG, PostGIS, the dashboard. They are deck material, and
none of them changes whether the core claim is credible.
