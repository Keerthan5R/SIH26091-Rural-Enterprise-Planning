"""Template narrator — the default, and the offline fallback lane (PLAN.md §4, §10).

Jinja over the facts object. It cannot hallucinate because it cannot invent: every placeholder
resolves against `facts.numeric_index`. It is still put through the validator, and the test suite
asserts it always passes — that is what makes the catch-rate metric meaningful for the LLM lane.
"""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined

from setubiz.facts.builder import Facts
from setubiz.money import format_inr, format_lakh
from setubiz.narration.base import Report, ReportSection
from setubiz.schemas import Language

TEMPLATE_FILE = Path(__file__).resolve().parent / "templates" / "report_sections.yaml"


class _Numbers(dict):
    """Attribute access over the facts numeric index, with a clear error on a missing key."""

    def __getattr__(self, key: str) -> Decimal:
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(
                f"report template referenced {key!r}, which is not in facts.numeric_index — "
                "add it to the facts object rather than computing it in a template"
            ) from exc


@lru_cache
def _document() -> dict[str, Any]:
    return yaml.safe_load(TEMPLATE_FILE.read_text(encoding="utf-8"))


@lru_cache
def _environment() -> Environment:
    env = Environment(undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)
    env.globals["fmt"] = format_inr
    env.globals["lakh"] = format_lakh
    return env


def _context(facts: Facts, language: Language) -> dict[str, Any]:
    reasons = _document()["binding_reason"][facts.right_sizing.binding.value]
    return {
        "facts": facts,
        "n": _Numbers(facts.numeric_index),
        "v": facts.village,
        "tpl": facts.template,
        "scheme": facts.scheme,
        "rs": facts.right_sizing,
        "rec": facts.right_sizing.recommended_loan,
        "lang": language.value,
        "binding_reason_en": reasons["en"],
        "binding_reason_hi": reasons["hi"],
        "binding_reason_kn": reasons["kn"],
        # Engine advisories about the competitor estimate itself. These fire when a block has no
        # Economic Census row for the category, which real data does hit -- and a band of 0-0
        # presented without that caveat reads as "no competition here", the opposite of what it
        # means. Rendering them is what keeps the band honest.
        "competitor_notes": tuple(n.text(language) for n in facts.competitors.notes),
    }


def _num(facts: Facts, key: str) -> Decimal | None:
    """A numeric-index value for a chart payload, or None when the key does not apply.

    The index is the single source of numbers; payloads never re-derive.
    """
    return facts.numeric_index.get(key)


def _chart_data(facts: Facts) -> dict[str, dict[str, Any]]:
    """Structured payloads the UI charts and stat rows read. Same numbers, never re-derived."""
    rs = facts.right_sizing
    seasonality = facts.threats.seasonality
    scheme = facts.scheme
    eligibility = facts.eligibility
    corporation = eligibility.corporation
    sca = eligibility.sca
    return {
        "headline": {
            "catchment_households": _num(facts, "households_now"),
            "villages_count": _num(facts, "villages_in_radius"),
            "radius_km": _num(facts, "radius_km"),
            "max_loan": rs.max_loan,
            "recommended_loan": rs.recommended_loan,
            "headroom": rs.headroom,
            "binding": rs.binding.value,
        },
        "loan_structure": {
            "max_loan": rs.max_loan,
            "recommended_loan": rs.recommended_loan,
            "headroom": rs.headroom,
            "required_capital": rs.required_capital,
            "debt_need": rs.debt_need,
            "binding": rs.binding.value,
            "dscr_threshold": rs.dscr_threshold,
            "margin": scheme.margin,
            "project_cost": scheme.project_cost,
            "scheme_name": scheme.scheme_name,
            "scheme_name_hi": scheme.scheme_name_hi or scheme.scheme_name,
            "annual_rate_pct": _num(facts, "annual_rate_pct"),
            "sca_rate_pct": _num(facts, "sca_rate_pct"),
            "tenure_years": _num(facts, "tenure_years"),
            "total_quarters": _num(facts, "total_quarters"),
            "moratorium_quarters": _num(facts, "moratorium_quarters"),
            "max_loan_min_dscr": rs.max_loan_min_dscr,
            "recommended_min_dscr": rs.recommended_min_dscr,
            "monthly_revenue": _num(facts, "monthly_revenue"),
            "monthly_opex": _num(facts, "monthly_opex"),
            "monthly_net": _num(facts, "monthly_net"),
        },
        "stress": {
            "dscr_threshold": rs.dscr_threshold,
            "stress_floor": rs.stress_floor,
            "monthly_revenue": _num(facts, "monthly_revenue"),
            "monthly_opex": _num(facts, "monthly_opex"),
            "monthly_net": _num(facts, "monthly_net"),
            "annual_noi": _num(facts, "annual_noi"),
            "annual_noi_stress_15": _num(facts, "annual_noi_stress_15"),
            "annual_noi_stress_30": _num(facts, "annual_noi_stress_30"),
            "recommended_stress_dscr_15": _num(facts, "recommended_min_dscr_stress_15"),
            "max_loan_stress_dscr_15": _num(facts, "max_loan_min_dscr_stress_15"),
            "max_loan": [
                {"year": r.year, "dscr": r.dscr, "debt_service": r.debt_service}
                for r in rs.max_loan_dscr
            ],
            "recommended": [
                {"year": r.year, "dscr": r.dscr, "debt_service": r.debt_service}
                for r in rs.recommended_dscr
            ],
            "scenarios": [
                {
                    "label": s.label,
                    "min_dscr": s.min_dscr,
                    "passes": s.passes,
                    "series": [{"year": r.year, "dscr": r.dscr} for r in s.by_year],
                }
                for s in rs.recommended_stress
            ],
        },
        "repayment": {
            "mode": rs.mode.value,
            "quarterly_instalment": _num(facts, "quarterly_instalment_recommended"),
            "total_interest": _num(facts, "total_interest_recommended"),
            "quarterly_instalment_max": _num(facts, "quarterly_instalment_max"),
            "total_interest_max": _num(facts, "total_interest_max"),
            "tenure_years": _num(facts, "tenure_years"),
            "total_quarters": _num(facts, "total_quarters"),
            "moratorium_quarters": _num(facts, "moratorium_quarters"),
            "repayment_quarters": _num(facts, "repayment_quarters"),
            "annual_rate_pct": _num(facts, "annual_rate_pct"),
            "sca_rate_pct": _num(facts, "sca_rate_pct"),
            "recommended": [
                r.__dict__
                for r in (
                    facts.amortization_recommended.schedule
                    if facts.amortization_recommended
                    else ()
                )
            ],
            "alternate_mode": (
                facts.amortization_alternate_mode.mode.value
                if facts.amortization_alternate_mode
                else None
            ),
            "alternate_instalment": (
                facts.amortization_alternate_mode.instalment
                if facts.amortization_alternate_mode
                else None
            ),
        },
        "market_reach": {
            "radius_km": _num(facts, "radius_km"),
            "households_2011": _num(facts, "households_2011"),
            "population_2011": _num(facts, "population_2011"),
            "households_now": _num(facts, "households_now"),
            "population_now": _num(facts, "population_now"),
            "growth_factor": _num(facts, "growth_factor"),
            "villages_with_bank": _num(facts, "villages_with_bank"),
            "road_connected_pct": _num(facts, "road_connected_pct"),
            "mandis_in_radius": _num(facts, "mandis_in_radius"),
            "demand_per_household_low": _num(facts, "demand_per_household_low"),
            "demand_per_household_high": _num(facts, "demand_per_household_high"),
            "addressable_market_low": _num(facts, "addressable_market_low"),
            "addressable_market_high": _num(facts, "addressable_market_high"),
            "addressable_market_point": _num(facts, "addressable_market_point"),
            "villages": [
                {
                    "name": n.village.name,
                    "name_hi": n.village.name_hi,
                    "name_kn": n.village.name_kn,
                    "distance_km": n.distance_km,
                    "households_2011": n.village.households_2011,
                    "lat": n.village.lat,
                    "lon": n.village.lon,
                    "has_bank": n.village.has_bank,
                }
                for n in facts.market.neighbours
            ],
            "income_segments": [
                {"label": s.label, "share": s.share, "households": s.households}
                for s in facts.market.income_segments
            ],
        },
        "competition": {
            "band": facts.competitors.band.model_dump(),
            "observed_osm": facts.competitors.osm_observed,
            "z_score": facts.competitors.z_score,
            "estimator": facts.competitors.method,
        },
        "scheme": {
            "scheme_name": scheme.scheme_name,
            "scheme_name_hi": scheme.scheme_name_hi or scheme.scheme_name,
            "logic": scheme.logic.value,
            "annual_rate_pct": _num(facts, "annual_rate_pct"),
            "sca_rate_pct": _num(facts, "sca_rate_pct"),
            "verdict": eligibility.verdict.value,
            "corporation_name": corporation.name if corporation else None,
            "corporation_name_hi": corporation.name_hi if corporation else None,
            "annual_family_income": eligibility.annual_family_income,
            "income_ceiling": eligibility.income_ceiling,
            "income_status": (
                "provided" if eligibility.annual_family_income is not None else "missing"
            ),
            "sca": (
                {
                    "name": sca.name,
                    "name_hi": sca.name_hi,
                    "address": sca.address,
                    "channel": sca.channel,
                }
                if sca
                else None
            ),
        },
        "stress_seasonality": (
            {
                "commodity": seasonality.commodity,
                "market": seasonality.market,
                "months": list(seasonality.months),
                "arrivals": list(seasonality.arrivals),
                "modal_price": list(seasonality.modal_price),
                "cv": seasonality.coefficient_of_variation,
                "peak_month": seasonality.peak_month,
                "trough_month": seasonality.trough_month,
            }
            if seasonality
            else {}
        ),
    }


class TemplateNarrator:
    name = "template"

    def narrate(self, facts: Facts, language: Language = Language.EN) -> Report:
        env = _environment()
        context = _context(facts, language)
        charts = _chart_data(facts)
        suffix = language.value

        sections: list[ReportSection] = []
        for spec in _document()["sections"]:
            body = env.from_string(spec[f"body_{suffix}"]).render(**context)
            sections.append(
                ReportSection(
                    id=spec["id"],
                    heading=spec[f"heading_{suffix}"],
                    body=" ".join(body.split()),
                    cites=tuple(spec.get("cites", ())),
                    data=charts.get(spec["id"], {}),
                )
            )

        if facts.group is not None:
            sections.append(_group_section(facts, language))
        sections.append(_alternatives_section(facts, language))
        sections.append(_stacking_section(facts, language))
        sections.append(_swot_section(facts, language))
        sections.append(_threats_section(facts, language))
        return Report(language=language, narrator=self.name, sections=tuple(sections))


def _plural(count: int, word: str) -> str:
    """English pluralisation for the one section that counts things in prose.

    Hindi does not take an English plural, so the Hindi branches never call this.
    """
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _pick(language: Language, en: str, hi: str, kn: str | None = None) -> str:
    """Select prose for the reader's language, falling back to English when Kannada is absent.

    English and Hindi behaviour is unchanged: `hi` is returned verbatim, never re-derived.
    """
    if language is Language.KN:
        return kn or en
    return hi if language is Language.HI else en


def _pick_seq(
    language: Language,
    en: tuple[str, ...],
    hi: tuple[str, ...],
    kn: tuple[str, ...] | None = None,
) -> list[str]:
    """Tuple form of `_pick`, for lists of names carried on one object."""
    if language is Language.KN:
        return list(kn or en)
    return list(hi if language is Language.HI else en)


def _alternatives_section(facts: Facts, language: Language) -> ReportSection:
    """Sizes of the same business that do work.

    Built programmatically rather than from a Jinja template because the number of rows varies
    and because the honest empty case carries bilingual advisories the engine already wrote.
    """
    alt = facts.alternatives
    label = _pick(
        language,
        alt.unit_label,
        alt.unit_label_hi or alt.unit_label,
        getattr(alt, "unit_label_kn", None),
    )

    rows = [
        {
            "units": c.units,
            "project_cost": c.project_cost,
            "loan": c.loan,
            "instalment": c.instalment,
            "min_dscr": c.min_dscr,
            "comfort": c.comfort,
            "self_financed": c.self_financed,
        }
        for c in alt.configurations
    ]

    if rows:
        lead = _pick(
            language,
            (
                "One size of this business clears the appraisal norm and is fully funded by "
                "your savings plus the loan it supports."
                if len(rows) == 1
                else f"{len(rows)} sizes of this business clear the appraisal norm and are "
                f"fully funded by your savings plus the loan they support."
            ),
            f"इस व्यवसाय के {len(rows)} आकार ऐसे हैं जो मानक भी पूरा करते हैं और आपकी बचत "
            f"एवं ऋण से पूरी तरह वित्तपोषित भी हो जाते हैं।",
            f"ಈ ವ್ಯವಹಾರದ {len(rows)} ಗಾತ್ರಗಳು ಮೌಲ್ಯಮಾಪನ ಮಾನದಂಡವನ್ನೂ ಪೂರೈಸುತ್ತವೆ ಮತ್ತು "
            f"ನಿಮ್ಮ ಉಳಿತಾಯ ಹಾಗೂ ಅವುಗಳಿಗೆ ಸಿಗುವ ಸಾಲದಿಂದ ಪೂರ್ಣ ಹಣಕಾಸು ಸಿಗುತ್ತದೆ.",
        )
        parts = [lead]
        for c in alt.configurations:
            if c.self_financed:
                parts.append(
                    _pick(
                        language,
                        f"{_plural(c.units, label)}: {format_inr(c.project_cost)}, "
                        "no borrowing needed.",
                        f"{c.units} {label}: {format_inr(c.project_cost)}, ऋण की आवश्यकता नहीं।",
                        f"{c.units} {label}: {format_inr(c.project_cost)}, ಸಾಲ ಬೇಕಿಲ್ಲ.",
                    )
                )
            else:
                parts.append(
                    _pick(
                        language,
                        f"{_plural(c.units, label)}: {format_inr(c.project_cost)}, borrow "
                        f"{format_inr(c.loan)}, {format_inr(c.instalment)} a quarter.",
                        f"{c.units} {label}: {format_inr(c.project_cost)}, ऋण "
                        f"{format_inr(c.loan)}, प्रति तिमाही {format_inr(c.instalment)}।",
                        f"{c.units} {label}: {format_inr(c.project_cost)}, ಸಾಲ "
                        f"{format_inr(c.loan)}, ಪ್ರತಿ ತ್ರೈಮಾಸಿಕಕ್ಕೆ {format_inr(c.instalment)}.",
                    )
                )
    else:
        parts = [a.text(language) for a in alt.why_not]

    phased = None
    if alt.phased is not None:
        p = alt.phased
        phased = {
            "start_units": p.start_units,
            "target_units": p.target_units,
            "expansion_cost": p.expansion_cost,
            "annual_retained": p.annual_retained,
            "years_to_expand": p.years_to_expand,
        }
        parts.append(
            _pick(
                language,
                f"You could start at {_plural(p.start_units, label)} and reach "
                f"{_plural(p.target_units, label)} in about {_plural(p.years_to_expand, 'year')} "
                f"from what the business retains, without a second loan.",
                f"आप {p.start_units} {label} से शुरू करके लगभग {p.years_to_expand} वर्ष में "
                f"{p.target_units} तक पहुँच सकते हैं, बिना दूसरा ऋण लिए।",
                f"ನೀವು {p.start_units} {label} ನಿಂದ ಪ್ರಾರಂಭಿಸಿ ಸುಮಾರು {p.years_to_expand} ವರ್ಷಗಳಲ್ಲಿ "
                f"{p.target_units} ತಲುಪಬಹುದು, ಇನ್ನೊಂದು ಸಾಲ ಬೇಕಿಲ್ಲದೆ.",
            )
        )

    return ReportSection(
        id="alternatives",
        heading=_pick(language, "Sizes that work", "जो आकार चल सकते हैं", "ಕೆಲಸ ಮಾಡುವ ಗಾತ್ರಗಳು"),
        body=" ".join(parts),
        cites=alt.sources,
        data={
            "unit_label": label,
            # The what-if sliders need the same bounds the search used, so a reader cannot drag
            # to a size the cost template was never meant to describe.
            "base_units": facts.template.base_units,
            "unit_range": list(facts.template.unit_range),
            "unit_step": facts.template.unit_step,
            "category": facts.template.category,
            "configurations": rows,
            "considered": [
                {
                    "units": c.units,
                    "project_cost": c.project_cost,
                    "shortfall": c.shortfall,
                    "funded": c.funded,
                }
                for c in alt.considered
            ],
            "closest_units": alt.closest.units if alt.closest else None,
            "additional_margin_needed": alt.additional_margin_needed,
            "phased": phased,
        },
    )


def _stacking_section(facts: Facts, language: Language) -> ReportSection:
    """Which of the schemes on this report may be held together.

    Confirmed combinations and unverified ones are kept in separate buckets all the way to the
    UI. Collapsing them into one list is how "confirm this at the district office" turns into
    "you qualify for both", which is the failure this feature exists to prevent.
    """
    st = facts.stacking

    def _render(combos):
        return [
            {
                "schemes": list(c.schemes),
                "names": _pick_seq(language, c.names, c.names_hi, getattr(c, "names_kn", None)),
                "reason": _pick(language, c.reason_en, c.reason_hi, getattr(c, "reason_kn", None)),
                "source": c.source,
                "sequencing": c.sequencing,
                "combined_cap": c.combined_cap,
                "subsidy_delta_pct": c.subsidy_delta_pct,
            }
            for c in combos
        ]

    parts: list[str] = []
    if st.combinable:
        parts.append(
            _pick(
                language,
                f"{len(st.combinable)} of the schemes on this report can be held together.",
                f"इस रिपोर्ट की {len(st.combinable)} योजनाएँ साथ ली जा सकती हैं।",
                f"ಈ ವರದಿಯ {len(st.combinable)} ಯೋಜನೆಗಳನ್ನು ಒಟ್ಟಿಗೆ ತೆಗೆದುಕೊಳ್ಳಬಹುದು.",
            )
        )
        parts.extend(
            _pick(language, c.reason_en, c.reason_hi, getattr(c, "reason_kn", None))
            for c in st.combinable
        )
    if st.needs_verification:
        parts.append(
            _pick(
                language,
                "These may combine, but we could not find an authoritative source either way. "
                "Confirm at the district office before counting on both.",
                "ये साथ मिल सकती हैं, किंतु हमें कोई आधिकारिक स्रोत नहीं मिला। दोनों पर भरोसा "
                "करने से पहले जिला कार्यालय से पुष्टि करें।",
                "ಇವು ಒಟ್ಟಿಗೆ ಸೇರಬಹುದು, ಆದರೆ ನಮಗೆ ಅಧಿಕೃತ ಮೂಲ ಸಿಗಲಿಲ್ಲ. ಎರಡನ್ನೂ ಲೆಕ್ಕಕ್ಕೆ "
                "ತೆಗೆದುಕೊಳ್ಳುವ ಮೊದಲು ಜಿಲ್ಲಾ ಕಚೇರಿಯಲ್ಲಿ ಖಚಿತಪಡಿಸಿಕೊಳ್ಳಿ.",
            )
        )
        parts.extend(
            _pick(language, c.reason_en, c.reason_hi, getattr(c, "reason_kn", None))
            for c in st.needs_verification
        )
    if st.mutually_exclusive:
        parts.append(
            _pick(
                language,
                "These cannot be held together.",
                "ये साथ नहीं ली जा सकतीं।",
                "ಇವನ್ನು ಒಟ್ಟಿಗೆ ತೆಗೆದುಕೊಳ್ಳಲಾಗದು.",
            )
        )
        parts.extend(
            _pick(language, c.reason_en, c.reason_hi, getattr(c, "reason_kn", None))
            for c in st.mutually_exclusive
        )
    if not parts:
        parts.append(
            _pick(
                language,
                "No scheme combinations apply to this application.",
                "इस आवेदन पर कोई योजना संयोजन लागू नहीं होता।",
                "ಈ ಅರ್ಜಿಗೆ ಯಾವುದೇ ಯೋಜನೆ ಸಂಯೋಜನೆ ಅನ್ವಯಿಸುವುದಿಲ್ಲ.",
            )
        )

    return ReportSection(
        id="stacking",
        heading=_pick(
            language,
            "Schemes you can hold together",
            "साथ ली जा सकने वाली योजनाएँ",
            "ಒಟ್ಟಿಗೆ ತೆಗೆದುಕೊಳ್ಳಬಹುದಾದ ಯೋಜನೆಗಳು",
        ),
        body=" ".join(parts),
        cites=st.sources,
        data={
            "combinable": _render(st.combinable),
            "needs_verification": _render(st.needs_verification),
            "mutually_exclusive": _render(st.mutually_exclusive),
            "considered": list(st.considered),
        },
    )


def _group_section(facts: Facts, language: Language) -> ReportSection:
    """The group's position, member by member.

    Anyone who does not qualify is named. A group-level verdict that quietly absorbed a failing
    member would send the group to the counter to discover it.
    """
    g = facts.group
    assert g is not None  # only called in group mode

    rows = [
        {
            "index": m.index,
            "name": m.name,
            "social_category": m.social_category,
            "contribution": m.contribution,
            "liability": m.liability,
            "corporation": m.corporation_name,
            "verdict": m.verdict.value,
            "qualifies": m.qualifies,
        }
        for m in g.members
    ]

    parts = [
        _pick(
            language,
            f"Group of {len(g.members)} members pooling {format_inr(g.pooled_margin)}.",
            f"{len(g.members)} सदस्यों का समूह, कुल {format_inr(g.pooled_margin)} की पूँजी।",
            f"{len(g.members)} ಸದಸ್ಯರ ಗುಂಪು, ಒಟ್ಟು {format_inr(g.pooled_margin)} ಬಂಡವಾಳ.",
        )
    ]
    if g.all_qualify:
        parts.append(
            _pick(
                language,
                "Every member qualifies.",
                "सभी सदस्य पात्र हैं।",
                "ಎಲ್ಲಾ ಸದಸ್ಯರು ಅರ್ಹರಾಗಿದ್ದಾರೆ.",
            )
        )
    else:
        parts.append(
            _pick(
                language,
                f"{len(g.qualifying)} of {len(g.members)} members qualify.",
                f"{len(g.members)} में से {len(g.qualifying)} सदस्य पात्र हैं।",
                f"{len(g.members)} ರಲ್ಲಿ {len(g.qualifying)} ಸದಸ್ಯರು ಅರ್ಹರಾಗಿದ್ದಾರೆ.",
            )
        )
    parts.extend(n.text(language) for n in g.notes)

    return ReportSection(
        id="group",
        heading=_pick(language, "Your group", "आपका समूह", "ನಿಮ್ಮ ಗುಂಪು"),
        body=" ".join(parts),
        cites=g.sources,
        data={
            "members": rows,
            "pooled_margin": g.pooled_margin,
            "liability_split": g.liability_split,
            "mixed_categories": g.mixed_categories,
            "routing_policy": g.routing_policy,
            "all_qualify": g.all_qualify,
        },
    )


def _swot_section(facts: Facts, language: Language) -> ReportSection:
    quadrants = {
        q: [
            _pick(language, i.text_en, i.text_hi, getattr(i, "text_kn", None))
            for i in facts.swot.by_quadrant(q)
        ]
        for q in ("strength", "weakness", "opportunity", "threat")
    }
    body = " ".join(line for lines in quadrants.values() for line in lines)
    return ReportSection(
        id="swot",
        heading=_pick(
            language,
            "Strengths, weaknesses, opportunities and threats",
            "ताकत, कमजोरी, अवसर एवं जोखिम",
            "ಬಲ, ದೌರ್ಬಲ್ಯ, ಅವಕಾಶ ಮತ್ತು ಅಪಾಯ",
        ),
        body=body,
        cites=tuple(dict.fromkeys(c for i in facts.swot.items for c in i.cites)),
        data={"quadrants": quadrants, "rules_fired": [i.id for i in facts.swot.items]},
    )


def _threats_section(facts: Facts, language: Language) -> ReportSection:
    items = [
        {
            "id": t.id,
            "severity": t.severity,
            "text": _pick(language, t.text_en, t.text_hi, getattr(t, "text_kn", None)),
        }
        for t in facts.threats.threats
    ]
    return ReportSection(
        id="threats",
        heading=_pick(language, "Risks to watch", "ध्यान देने योग्य जोखिम", "ಗಮನಿಸಬೇಕಾದ ಅಪಾಯಗಳು"),
        body=" ".join(i["text"] for i in items),
        cites=facts.threats.sources,
        data={
            "items": items,
            "price_band": facts.threats.price_band.model_dump()
            if facts.threats.price_band
            else None,
            "seasonality": _chart_data(facts)["stress_seasonality"],
        },
    )
