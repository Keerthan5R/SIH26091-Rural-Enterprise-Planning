import { inr, pick, pickLabel, SOCIAL_LABELS, type Strings } from '../format'
import type { Facts, Language } from '../types'
import type { AdvisoryInput } from '../api'

interface Props {
  facts: Facts
  input: AdvisoryInput | null
  language: Language
  strings: Strings
}

/** The paper identity of the report.
 *
 *  On screen this block is noise: the wizard knows who is asking. On paper the sheet travels
 *  without its context, to a bank counter where nobody knows which applicant, which business or
 *  which savings figure produced these numbers. So the printed document opens with the applicant's
 *  own inputs, restated from the URL the report was generated from, before any analysis. The
 *  block is always rendered and only ever visible in print. */
export function PrintHeader({ facts, input, language, strings }: Props) {
  const rows: { label: string; value: string }[] = [
    {
      label: strings.village,
      value: `${pick(language, facts.village.name, facts.village.name_hi ?? facts.village.name, facts.village.name_kn)}, ${facts.village.block}, ${facts.village.district}, ${facts.village.state}`,
    },
    {
      label: strings.business,
      value: `${pick(language, facts.template.name, facts.template.name_hi ?? facts.template.name, facts.template.name_kn)}`,
    },
    { label: strings.savings, value: inr(facts.scheme.margin) },
    {
      label: strings.income,
      value:
        input?.annual_family_income != null
          ? inr(input.annual_family_income)
          : strings.incomeMissing,
    },
    {
      label: strings.social,
      value: input ? pickLabel(SOCIAL_LABELS, input.social_category, language) : '',
    },
    { label: strings.woman, value: input?.is_woman ? strings.yes : strings.no },
    {
      label: strings.experienced,
      value: input?.has_prior_experience ? strings.yes : strings.no,
    },
    { label: strings.radius, value: `${input?.radius_km ?? 10} ${strings.km}` },
  ]

  return (
    <section className="setubiz-print-cover-head setubiz-print-head" aria-hidden="true">
      <div className="setubiz-print-cover-report-block">
        <h1 className="setubiz-print-cover-title setubiz-m-0">
          {pick(language, 'Rural Enterprise Planning Report', 'ग्रामीण उद्यम योजना रिपोर्ट', 'ಗ್ರಾಮೀಣ ಉದ್ಯಮ ಯೋಜನಾ ವರದಿ')}
        </h1>
        <div className="setubiz-print-cover-rule" aria-hidden="true" />
        <p className="setubiz-print-cover-plan setubiz-m-0">
          {pick(
            language,
            'Applicant Information and Business Plan',
            'आवेदक की जानकारी और व्यवसाय योजना',
            'ಅರ್ಜಿದಾರರ ಮಾಹಿತಿ ಮತ್ತು ಉದ್ಯಮ ಯೋಜನೆ',
          )}
        </p>
      </div>
      <table className="ux4g-table setubiz-print-inputs">
        <tbody>
          {rows.map((r) => (
            <tr key={r.label}>
              <th scope="row">{r.label}</th>
              <td className="setubiz-tabular">{r.value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
