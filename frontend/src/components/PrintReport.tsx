import { BandBar } from './BandBar'
import { CatchmentMap } from './CatchmentMap'
import { DistanceBands, IncomeSegments } from './DistanceBands'
import { DscrChart } from './DscrChart'
import { GroupPanel } from './GroupPanel'
import { LoanComparison } from './LoanComparison'
import { OutOfScope } from './OutOfScope'
import { PrintHeader } from './PrintHeader'
import { ScheduleTable } from './ScheduleTable'
import { SchemeStacking } from './SchemeStacking'
import { SeasonalityChart } from './SeasonalityChart'
import { SizesThatWork } from './SizesThatWork'
import { SwotGrid } from './SwotGrid'
import { StatRows } from './StatRows'
import { inr, lakh, pick, ratio, type Strings } from '../format'
import type { AdvisoryResponse, DscrYear, Language } from '../types'
import type { AdvisoryInput } from '../api'

interface Props {
  data: AdvisoryResponse
  input: AdvisoryInput | null
  language: Language
  strings: Strings
}

/** The printed sheet, ordered exactly as the problem statement numbers its requirements.
 *
 *  On screen the answer leads and the reasoning folds away, which is the right shape for a
 *  decision. On paper the reader is a judge or a bank officer checking the service against its
 *  brief, so the document follows the brief's own hierarchy: Module 1 with the six parameters in
 *  the PS's order and under the PS's names, then Module 2 with the margin rule, the scheme
 *  router and the repayment generator, and only then the appraisal that goes beyond the formula.
 *  Everything in this tree is print-only; the screen never shows it. */
export function PrintReport({ data, input, language, strings }: Props) {
  const { facts, report } = data
  const section = (id: string) => report.sections.find((s) => s.id === id)
  const num = (id: string) => facts.numeric_index[id]
  const stat = (id: string, fmt?: (v: string) => string) => {
    const raw = num(id)
    return raw === undefined ? undefined : fmt ? fmt(raw) : raw
  }
  const locale = language === 'hi' ? 'hi-IN' : language === 'kn' ? 'kn-IN' : 'en-IN'
  const int = (v: string) => Math.round(Number(v)).toLocaleString(locale)
  const villageName = pick(
    language,
    facts.village.name,
    facts.village.name_hi ?? facts.village.name,
    facts.village.name_kn,
  )
  const marketReach = section('market_reach')
  const competition = section('competition')
  const swot = section('swot')
  const threats = section('threats')
  const group = section('group')
  const stacking = section('stacking')
  const alternatives = section('alternatives')
  const outOfScope = Number(facts.right_sizing.max_loan) <= 0

  const splitModuleTitle = (title: string) => {
    const separator = title.indexOf(':')
    return separator === -1
      ? [title]
      : [title.slice(0, separator).trim(), title.slice(separator + 1).trim()]
  }

  return (
    <div className="setubiz-print-only setubiz-print-doc">
      <div className="setubiz-print-only setubiz-print-cover" aria-hidden="true">
        <p className="ux4g-body-s-default setubiz-print-cover-date setubiz-tabular setubiz-m-0">
          {strings.printGenerated}: {new Date(facts.generated_at).toLocaleString(locale)}
        </p>
        <div className="setubiz-print-cover-identity">
          <p className="setubiz-print-cover-id setubiz-m-0">SIH26091</p>
          <p className="setubiz-print-cover-major setubiz-m-0">
            {pick(language, 'MAJOR PROJECT', 'प्रमुख परियोजना', 'ಪ್ರಮುಖ ಯೋಜನೆ')}
          </p>
          <p className="setubiz-print-cover-system setubiz-m-0">
            {pick(
              language,
              'AI-Powered Rural Enterprise Planning System',
              'एआई-संचालित ग्रामीण उद्यम योजना प्रणाली',
              'ಎಐ ಆಧಾರಿತ ಗ್ರಾಮೀಣ ಉದ್ಯಮ ಯೋಜನಾ ವ್ಯವಸ್ಥೆ',
            )}
          </p>
        </div>
        <div className="setubiz-print-cover-frame">
          <PrintHeader facts={facts} input={input} language={language} strings={strings} />

          {facts.contains_synthetic_data ? (
          <div className="ux4g-alert ux4g-alert-warning ux4g-mt-m setubiz-print-block" role="status">
            <span className="ux4g-icon-outlined ux4g-alert-icon" aria-hidden="true">
              warning
            </span>
            <div className="ux4g-alert-content">
              <p className="ux4g-alert-title">{strings.synthetic}</p>
              <p className="ux4g-alert-message setubiz-measure">{strings.syntheticNote}</p>
            </div>
          </div>
        ) : (
          <div className="ux4g-alert ux4g-alert-info ux4g-mt-m setubiz-print-block" role="status">
            <span className="ux4g-icon-outlined ux4g-alert-icon" aria-hidden="true">
              verified
            </span>
            <div className="ux4g-alert-content">
              <p className="ux4g-alert-title">{strings.officialData}</p>
              <p className="ux4g-alert-message setubiz-measure">{strings.officialDataNote}</p>
            </div>
          </div>
	        )}
	      </div>
	      </div>

	      {group && <GroupPanel data={group.data} body={group.body} strings={strings} />}

      {/* ---------------- Module 1: the six parameters, in the PS's order ---------------- */}
      <h2 className="setubiz-print-module">
        {splitModuleTitle(strings.printModule1).map((line, index) => (
          <span className="setubiz-print-module-line" key={index}>
            {line}
          </span>
        ))}
        <span className="setubiz-print-module-rule" aria-hidden="true" />
      </h2>

      <h3 className="setubiz-print-param">{strings.psMarketReach}</h3>
      {marketReach && (
        <div className="setubiz-print-block">
          {marketReach.body && <p className="ux4g-body-m-default setubiz-measure">{marketReach.body}</p>}
          {marketReach.data.villages && marketReach.data.villages.length > 0 && (
            <>
              {(() => {
                const centre = marketReach.data.villages.reduce((a, b) =>
                  b.distance_km < a.distance_km ? b : a,
                )
                return (
                  <CatchmentMap
                    centreName={villageName}
                    centre={{ lat: centre.lat, lon: centre.lon }}
                    villages={marketReach.data.villages}
                    radiusKm={input?.radius_km ?? 10}
                    language={language}
                    strings={strings}
                  />
                )
              })()}
              <div className="ux4g-grid ux4g-grid-cols-1 ux4g-md-grid-cols-2 ux4g-gap-l ux4g-mt-m">
                <DistanceBands
                  villages={marketReach.data.villages}
                  radiusKm={input?.radius_km ?? 10}
                  language={language}
                />
                {marketReach.data.income_segments && (
                  <IncomeSegments segments={marketReach.data.income_segments} language={language} />
                )}
              </div>
              <div className="ux4g-mt-m">
                <StatRows
                  columns={3}
                  rows={[
                    { label: strings.statCatchment, value: stat('households_now', int) },
                    { label: strings.statPopulationNow, value: stat('population_now', int) },
                    { label: strings.statVillages, value: stat('villages_in_radius', int) },
                    { label: strings.statBankVillages, value: stat('villages_with_bank') },
                    { label: strings.statRoadPct, value: stat('road_connected_pct', (v) => `${Number(v)}%`) },
                    { label: strings.statMandis, value: stat('mandis_in_radius') },
                  ]}
                />
              </div>
              <details open className="setubiz-print-block ux4g-mt-m">
                <summary className="ux4g-body-m-default ux4g-text-neutral-secondary">
                  {strings.allVillages.replace('{n}', String(marketReach.data.villages.length))}
                </summary>
                <ul className="ux4g-d-flex ux4g-flex-wrap ux4g-gap-xs ux4g-mt-s">
                  {marketReach.data.villages.map((v) => (
                    <li key={v.name}>
                      <span className="ux4g-tag-tonal-neutral ux4g-tag-s setubiz-tabular">
                        {pick(language, v.name, v.name_hi ?? v.name, v.name_kn)} · {v.distance_km}{' '}
                        {strings.km}
                      </span>
                    </li>
                  ))}
                </ul>
              </details>
            </>
          )}
        </div>
      )}

      <h3 className="setubiz-print-param">{strings.psOpportunity}</h3>
      <div className="setubiz-print-block">
        <StatRows
          columns={3}
          rows={[
            {
              label: strings.statDemandPerHH,
              value:
                num('demand_per_household_low') !== undefined
                  ? `${inr(num('demand_per_household_low')!)} - ${inr(num('demand_per_household_high')!)}`
                  : undefined,
            },
            {
              label: strings.statAddressable,
              value:
                num('addressable_market_low') !== undefined
                  ? `${lakh(num('addressable_market_low')!)} - ${lakh(num('addressable_market_high')!)}`
                  : undefined,
            },
            { label: 'Demand-supply ratio', value: stat('demand_supply_ratio', ratio) },
            { label: strings.printHouseholdsPer, value: stat('households_per_competitor', ratio) },
          ]}
        />
        {section('headline')?.body && (
          <p className="ux4g-body-m-default setubiz-measure ux4g-mt-s">{section('headline')?.body}</p>
        )}
      </div>

      <h3 className="setubiz-print-param">{strings.psSwot}</h3>
      {swot?.data.quadrants && (
        <div className="setubiz-print-block">
          <SwotGrid quadrants={swot.data.quadrants} labels={strings.quadrant} />
        </div>
      )}

      <h3 className="setubiz-print-param">{strings.psThreats}</h3>
      <div className="setubiz-print-block">
        {(threats?.data.items ?? []).length > 0 && (
          <ul className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-s">
            {(threats?.data.items ?? []).map((item) => (
              <li className="ux4g-d-flex ux4g-ai-start ux4g-gap-x-s" key={item.id}>
                <span
                  className={`ux4g-tag-s ${
                    item.severity === 'high' ? 'ux4g-tag-tonal-error' : 'ux4g-tag-tonal-warning'
                  }`}
                >
                  {item.severity}
                </span>
                <span className="ux4g-body-m-default setubiz-measure">{item.text}</span>
              </li>
            ))}
          </ul>
        )}
        {threats?.data.seasonality?.months && (
          <div className="ux4g-mt-m">
            <SeasonalityChart
              months={threats.data.seasonality.months}
              arrivals={threats.data.seasonality.arrivals ?? []}
              commodity={threats.data.seasonality.commodity ?? ''}
              market={threats.data.seasonality.market ?? ''}
              peakMonth={threats.data.seasonality.peak_month}
              troughMonth={threats.data.seasonality.trough_month}
              language={language}
            />
          </div>
        )}
      </div>

      <h3 className="setubiz-print-param">{strings.psCompetitors}</h3>
      {competition?.data.band && (
        <div className="setubiz-print-block">
          <BandBar
            band={competition.data.band}
            format={(v) => String(Math.round(Number(v)))}
            label={strings.existingEnterprises}
            language={language}
          />
          <div className="ux4g-mt-m">
            <StatRows
              columns={3}
              rows={[
                { label: strings.printDensity, value: stat('competitor_density_per_1k_households', ratio) },
                { label: strings.printHouseholdsPer, value: stat('households_per_competitor', ratio) },
                { label: 'OpenStreetMap', value: competition.data.observed_osm !== undefined ? String(competition.data.observed_osm) : undefined },
              ]}
            />
          </div>
          {competition.body && (
            <p className="ux4g-body-m-default setubiz-measure ux4g-mt-s">{competition.body}</p>
          )}
        </div>
      )}

      <h3 className="setubiz-print-param">{strings.psPrice}</h3>
      <div className="setubiz-print-block">
        {threats?.data.price_band && (
          <BandBar
            band={threats.data.price_band}
            format={(v) => inr(v)}
            label={strings.priceSpread}
            language={language}
          />
        )}
        <div className="ux4g-mt-m">
          <StatRows
            columns={3}
            rows={[
              {
                label: strings.statDemandPerHH,
                value:
                  num('demand_per_household_low') !== undefined
                    ? `${inr(num('demand_per_household_low')!)} - ${inr(num('demand_per_household_high')!)}`
                    : undefined,
              },
              { label: strings.statMonthlyRevenue, value: stat('monthly_revenue', inr) },
              { label: strings.statMonthlyOpex, value: stat('monthly_opex', inr) },
            ]}
          />
        </div>
      </div>

      {/* ---------------- Module 2: calculator and router, in the PS's own table order --------- */}
      <h2 className="setubiz-print-module setubiz-print-module--new-page">
        {splitModuleTitle(strings.printModule2).map((line, index) => (
          <span className="setubiz-print-module-line" key={index}>
            {line}
          </span>
        ))}
        <span className="setubiz-print-module-rule" aria-hidden="true" />
      </h2>

      <table className="ux4g-table setubiz-print-rules setubiz-print-block">
        <thead>
          <tr>
            <th scope="col">{pick(language, 'Financial parameter', 'वित्तीय पैरामीटर', 'ಹಣಕಾಸು ನಿಯತಾಂಕ')}</th>
            <th scope="col">{strings.printRuleCol}</th>
            <th scope="col">{strings.printValueCol}</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row">{strings.printMarginRow}</th>
            <td>{pick(language, '10% promoter contribution (applicant savings)', '10% अंशदान (आवेदक की बचत)', '10% ಅಂಶದಾನ (ಅರ್ಜಿದಾರರ ಉಳಿತಾಯ)')}</td>
            <td className="setubiz-tabular">{inr(facts.scheme.margin)}</td>
          </tr>
          <tr>
            <th scope="row">{pick(language, 'Total project cost', 'कुल परियोजना लागत', 'ಒಟ್ಟು ಯೋಜನಾ ವೆಚ್ಚ')}</th>
            <td>{pick(language, 'Margin ÷ 10%', 'मार्जिन ÷ 10%', 'ಮಾರ್ಜಿನ್ ÷ 10%')}</td>
            <td className="setubiz-tabular">{inr(facts.scheme.project_cost)}</td>
          </tr>
          <tr>
            <th scope="row">{pick(language, 'Maximum loan', 'अधिकतम ऋण', 'ಗರಿಷ್ಠ ಸಾಲ')}</th>
            <td>{pick(language, '90% of project cost, up to the scheme cap', 'परियोजना लागत का 90%, योजना सीमा तक', 'ಯೋಜನಾ ವೆಚ್ಚದ 90%, ಯೋಜನಾ ಮಿತಿಯವರೆಗೆ')}</td>
            <td className="setubiz-tabular">{inr(facts.scheme.max_loan)}</td>
          </tr>
          <tr>
            <th scope="row">{strings.printLogicRow}</th>
            <td>
              {facts.scheme.logic === 'A'
                ? pick(
                    language,
                    'Logic A: 6.5% p.a., 3-year tenure, 3-month moratorium',
                    'लॉजिक A: 6.5% वार्षिक, 3 वर्ष, 3-माह अधिस्थगन',
                    'ಲಾಜಿಕ್ A: 6.5% ವಾರ್ಷಿಕ, 3 ವರ್ಷ, 3-ತಿಂಗಳ ಮೊರಟೋರಿಯಂ',
                  )
                : facts.scheme.logic === 'B'
                  ? pick(
                      language,
                      'Logic B: 8.0% p.a., 7-year tenure, 6-month moratorium',
                      'लॉजिक B: 8.0% वार्षिक, 7 वर्ष, 6-माह अधिस्थगन',
                      'ಲಾಜಿಕ್ B: 8.0% ವಾರ್ಷಿಕ, 7 ವರ್ಷ, 6-ತಿಂಗಳ ಮೊರಟೋರಿಯಂ',
                    )
                  : pick(language, 'out of scheme scope', 'स्कीम दायरे से बाहर', 'ಯೋಜನಾ ವ್ಯಾಪ್ತಿಯ ಹೊರಗೆ')}
            </td>
            <td className="setubiz-tabular">{facts.scheme.scheme_name}</td>
          </tr>
          <tr>
            <th scope="row">{pick(language, 'Repayment generator', 'चुकौती जनरेटर', 'ಮರುಪಾವತಿ ಜನರೇಟರ್')}</th>
            <td>{pick(language, 'quarterly schedule, moratorium-aware, working capital included', 'तिमाही अनुसूची, अधिस्थगन-सजग, कार्यशील पूँजी सहित', 'ತ್ರೈಮಾಸಿಕ ವೇಳಾಪಟ್ಟಿ, ಮೊರಟೋರಿಯಂ-ಅರಿವಿನ, ಕಾರ್ಯನಿರತ ಬಂಡವಾಳ ಸೇರಿದಂತೆ')}</td>
            <td className="setubiz-tabular">
              {facts.amortization_recommended
                ? `${inr(facts.amortization_recommended.instalment)} / ${pick(language, 'quarter', 'तिमाही', 'ತ್ರೈಮಾಸಿಕ')}`
                : pick(language, 'not applicable', 'लागू नहीं', 'ಅನ್ವಯಿಸುವುದಿಲ್ಲ')}
            </td>
          </tr>
        </tbody>
      </table>

      <h3 className="setubiz-print-param">{strings.printAppraisal}</h3>
      {outOfScope ? (
        <OutOfScope facts={facts} language={language} strings={strings} />
      ) : (
        <div className="setubiz-print-block">
          <LoanComparison
            maxLoan={facts.scheme.max_loan}
            recommendedLoan={facts.right_sizing.recommended_loan}
            headroom={facts.right_sizing.headroom}
            requiredCapital={facts.right_sizing.required_capital}
            debtNeed={facts.right_sizing.debt_need}
            binding={facts.right_sizing.binding}
            maxMinDscr={facts.right_sizing.max_loan_min_dscr}
            recommendedMinDscr={facts.right_sizing.recommended_min_dscr}
            dscrThreshold={facts.right_sizing.dscr_threshold}
            language={language}
            strings={strings}
          />
          {!outOfScope && alternatives && (
            <div className="ux4g-mt-l">
              <SizesThatWork data={alternatives.data} language={language} strings={strings} />
            </div>
          )}
          {section('stress')?.data.recommended && (
            <div className="ux4g-mt-l">
              <DscrChart
                base={(section('stress')!.data.recommended as DscrYear[]) ?? []}
                scenarios={section('stress')!.data.scenarios ?? []}
                threshold={facts.right_sizing.dscr_threshold}
                stressFloor={facts.right_sizing.stress_floor}
                language={language}
              />
            </div>
          )}
          {section('repayment') && facts.amortization_recommended && (
            <div className="ux4g-mt-l">
              <ScheduleTable
                rows={facts.amortization_recommended.schedule}
                mode={section('repayment')!.data.mode ?? 'serviced'}
                alternateMode={facts.amortization_alternate_mode?.mode ?? null}
                alternateInstalment={facts.amortization_alternate_mode?.instalment ?? null}
                language={language}
                strings={strings}
                showAll
                showTotals
              />
            </div>
          )}
        </div>
      )}

      {stacking && <SchemeStacking data={stacking.data} strings={strings} />}

      {facts.warnings.length > 0 && (
        <div className="setubiz-print-block setubiz-mt-m">
          <h3 className="setubiz-print-param">{strings.warningsHeading}</h3>
          <ul className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-xs">
            {facts.warnings.map((w) => (
              <li className="ux4g-body-m-default setubiz-measure" key={w.id}>
                {pick(language, w.text_en, w.text_hi, w.text_kn)}
              </li>
            ))}
          </ul>
        </div>
      )}

      <section className="ux4g-card ux4g-card-outline ux4g-mt-l setubiz-print-block" id="eligibility-print">
        <div className="ux4g-card-header">
          <h2 className="ux4g-heading-m-strong ux4g-card-title">
            {section('scheme')?.heading ?? strings.apply}
          </h2>
        </div>
        <div className="ux4g-card-body ux4g-d-flex ux4g-flex-column ux4g-gap-y-m">
          {section('scheme')?.body && <p className="ux4g-body-m-default setubiz-measure">{section('scheme')?.body}</p>}
          <div className="ux4g-d-flex ux4g-ai-center ux4g-gap-x-s ux4g-flex-wrap">
            <span
              className={`ux4g-tag-s ${
                facts.eligibility.verdict === 'eligible'
                  ? 'ux4g-tag-tonal-success'
                  : facts.eligibility.verdict === 'ineligible'
                    ? 'ux4g-tag-tonal-error'
                    : 'ux4g-tag-tonal-warning'
              }`}
            >
              {facts.eligibility.verdict === 'eligible'
                ? strings.verdictEligible
                : facts.eligibility.verdict === 'ineligible'
                  ? strings.verdictIneligible
                  : strings.verdictConditions}
            </span>
            {facts.eligibility.corporation && (
              <span className="ux4g-body-m-default ux4g-text-neutral-secondary">
                {pick(
                  language,
                  facts.eligibility.corporation.name,
                  facts.eligibility.corporation.name_hi ?? facts.eligibility.corporation.name,
                  facts.eligibility.corporation.name_kn,
                )}
              </span>
            )}
          </div>

          {facts.eligibility.reasons.length > 0 && (
            <div>
              <h3 className="ux4g-title-s-strong ux4g-mb-xs">{strings.reasonsHeading}</h3>
              <ul className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-xs">
                {(language === 'kn' && facts.eligibility.reasons_kn?.length
                  ? facts.eligibility.reasons_kn
                  : language === 'hi' && facts.eligibility.reasons_hi?.length
                    ? facts.eligibility.reasons_hi
                    : facts.eligibility.reasons
                ).map((reason) => (
                  <li className="ux4g-body-m-default setubiz-measure" key={reason}>
                    {reason}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {facts.eligibility.conditions.length > 0 && (
            <div>
              <h3 className="ux4g-title-s-strong ux4g-mb-xs">{strings.conditionsHeading}</h3>
              <ul className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-xs">
                {(language === 'kn' && facts.eligibility.conditions_kn?.length
                  ? facts.eligibility.conditions_kn
                  : language === 'hi' && facts.eligibility.conditions_hi?.length
                    ? facts.eligibility.conditions_hi
                    : facts.eligibility.conditions
                ).map((condition) => (
                  <li className="ux4g-body-m-default setubiz-measure" key={condition}>
                    {condition}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div>
            <h3 className="ux4g-title-s-strong ux4g-mb-s">{strings.documents}</h3>
            <ul className="ux4g-d-flex ux4g-flex-column ux4g-gap-y-xs">
              {facts.eligibility.documents.map((doc) => (
                <li className="ux4g-body-s-default" key={doc.en}>
                  <span className="ux4g-icon-outlined ux4g-text-neutral-tertiary" aria-hidden="true">
                    check_box_outline_blank
                  </span>{' '}
                  {pick(language, doc.en, doc.hi ?? doc.en, doc.kn)}
                </li>
              ))}
            </ul>
          </div>

          {facts.eligibility.sca && (
            <div>
              <h3 className="ux4g-title-s-strong ux4g-mb-xs">{strings.apply}</h3>
              <p className="ux4g-body-m-default setubiz-measure">
                {pick(language, facts.eligibility.sca.name, facts.eligibility.sca.name_hi ?? facts.eligibility.sca.name, facts.eligibility.sca.name_kn)}
                <br />
                {facts.eligibility.sca.address}
                <br />
                {facts.eligibility.sca.channel}
              </p>
            </div>
          )}
        </div>
      </section>

      {/* ---------------- Sources: the judge's "where did that number come from" answer ---------- */}
      <h3 className="setubiz-print-param">{strings.printSources}</h3>
      <ol className="ux4g-body-s-default ux4g-text-neutral-secondary setubiz-print-sources">
        {facts.sources.map((s) => (
          <li key={s.id}>
            {s.title}
            {s.publisher ? ` · ${s.publisher}` : ''}
            {s.year ? ` · ${s.year}` : ''}
          </li>
        ))}
      </ol>
      <section className="setubiz-print-block ux4g-mt-m">
        <h3 className="setubiz-print-param">{strings.provenance}</h3>
        <div className="ux4g-table-responsive">
          <table className="ux4g-table ux4g-table-s setubiz-print-rules">
            <thead>
              <tr>
                <th scope="col">{pick(language, 'Figure', 'आँकड़ा', 'ಅಂಕಿ')}</th>
                <th scope="col">{pick(language, 'Source', 'स्रोत', 'ಮೂಲ')}</th>
              </tr>
            </thead>
            <tbody className="setubiz-tabular">
              {Object.entries(facts.numeric_index)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([key, value]) => (
                  <tr key={key}>
                    <th scope="row">{key}: {value}</th>
                    <td>
                      {(facts.provenance[key] ?? [])
                        .map((id) => facts.sources.find((source) => source.id === id))
                        .filter(Boolean)
                        .map((source, index) => (
                          <span key={source!.id}>
                            {index > 0 ? ' · ' : null}
                            {source!.title}
                            {source!.year ? ` (${source!.year})` : ''}
                            {source!.synthetic
                              ? ` · ${pick(language, 'sample', 'नमूना', 'ಮಾದರಿ')}`
                              : ` · ${pick(language, 'official', 'आधिकारिक', 'ಅಧಿಕೃತ')}`}
                          </span>
                        ))}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </section>

      <p className="ux4g-body-s-default ux4g-text-neutral-tertiary setubiz-measure setubiz-mt-m">
        {section('data_note')?.body}
      </p>

      <p className="ux4g-body-s-default ux4g-text-neutral-tertiary setubiz-tabular ux4g-mt-s">
        {data.validation.checked} {strings.grounded} · {strings.narrator}: {data.report.narrator}
      </p>
    </div>
  )
}
