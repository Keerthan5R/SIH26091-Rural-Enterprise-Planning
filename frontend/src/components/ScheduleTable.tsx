import { useState } from 'react'
import { inr, pick, type Strings } from '../format'
import type { Language, ScheduleRow } from '../types'

interface Props {
  rows: ScheduleRow[]
  mode: string
  alternateMode: string | null
  alternateInstalment: string | null
  language: Language
  strings: Strings
  /** Print renders the whole schedule; the screen keeps the compact six-row view. */
  showAll?: boolean
  /** Print also shows a totals row, which the interactive view omits. */
  showTotals?: boolean
}

const HEAD = {
  en: ['Qtr', 'Opening', 'Interest', 'Principal', 'Instalment', 'Closing'],
  hi: ['तिमाही', 'प्रारंभिक शेष', 'ब्याज', 'मूलधन', 'किस्त', 'अंतिम शेष'],
  kn: ['ತ್ರೈಮಾಸಿಕ', 'ಆರಂಭಿಕ ಬಾಕಿ', 'ಬಡ್ಡಿ', 'ಅಸಲು', 'ಕಂತು', 'ಅಂತಿಮ ಬಾಕಿ'],
}

export function ScheduleTable({
  rows,
  mode,
  alternateMode,
  alternateInstalment,
  language,
  strings,
  showAll = false,
  showTotals = false,
}: Props) {
  const [expanded, setExpanded] = useState(showAll)
  if (!rows.length) return null
  const shown = showAll || expanded ? rows : rows.slice(0, 6)

  return (
    <div className="setubiz-print-block ux4g-d-flex ux4g-flex-column ux4g-gap-y-s">
      <p className="ux4g-body-m-default ux4g-text-neutral-secondary setubiz-measure">
        {pick(language, 'Moratorium interest: ', 'अधिस्थगन ब्याज: ', 'ಮೊರಟೋರಿಯಂ ಬಡ್ಡಿ: ')}
        <strong>
          {mode === 'serviced'
            ? pick(language, 'paid each quarter', 'हर तिमाही चुकाया', 'ಪ್ರತಿ ತ್ರೈಮಾಸಿಕ ಪಾವತಿಸಲಾಗುತ್ತದೆ')
            : pick(language, 'added to principal', 'मूलधन में जोड़ा', 'ಅಸಲಿಗೆ ಸೇರಿಸಲಾಗುತ್ತದೆ')}
        </strong>
      </p>

      {/* The alternate moratorium treatment is not a question the reader is asked during the form
          — it is jargon they have no basis to answer. It is shown here instead, already computed,
          as a comparison they can take to the bank. */}
      {alternateInstalment && (
        <p className="ux4g-body-m-default ux4g-text-neutral-secondary setubiz-measure">
          {strings.moratoriumAlt}{' '}
          <span className="setubiz-tabular">{inr(alternateInstalment)}</span>
          {pick(language, ` a quarter (${alternateMode})`, ' प्रति तिमाही', ' ಪ್ರತಿ ತ್ರೈಮಾಸಿಕ')}
        </p>
      )}

      <div className="ux4g-table-responsive">
        <table className="ux4g-table ux4g-table-m ux4g-table-zebra-rows ux4g-table-rounded">
          <thead>
            <tr>
              {HEAD[language].map((h) => (
                <th key={h} scope="col">
                  <span className="ux4g-table-th-content">{h}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="setubiz-tabular">
            {shown.map((row) => (
              <tr key={row.quarter}>
                <th scope="row">
                  {row.quarter}
                  {row.phase === 'moratorium' && (
                    <span className="ux4g-tag-tonal-warning ux4g-tag-s ux4g-ml-xs">
                      {pick(language, 'moratorium', 'अधिस्थगन', 'ಮೊರಟೋರಿಯಂ')}                    </span>
                  )}
                </th>
                <td>{inr(row.opening)}</td>
                <td>{inr(row.interest)}</td>
                <td>{inr(row.principal)}</td>
                <td>
                  <strong>{inr(row.instalment)}</strong>
                </td>
                <td>{inr(row.closing)}</td>
              </tr>
            ))}
            {showTotals && (
              <tr className="setubiz-schedule-total">
                <th scope="row">{pick(language, 'Total', 'कुल', 'ಒಟ್ಟು')}</th>
                <td>-</td>
                <td>{inr(rows.reduce((sum, row) => sum + Number(row.interest), 0).toFixed(2))}</td>
                <td>{inr(rows.reduce((sum, row) => sum + Number(row.principal), 0).toFixed(2))}</td>
                <td>
                  <strong>{inr(rows.reduce((sum, row) => sum + Number(row.instalment), 0).toFixed(2))}</strong>
                </td>
                <td>-</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {rows.length > 6 && !showAll && (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="ux4g-btn ux4g-btn-text-primary ux4g-btn-lg setubiz-no-print"
        >
          {expanded ? strings.hideSchedule : `${strings.showSchedule} (${rows.length})`}
        </button>
      )}
    </div>
  )
}
