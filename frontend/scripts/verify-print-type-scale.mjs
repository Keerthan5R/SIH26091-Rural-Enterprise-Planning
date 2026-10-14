#!/usr/bin/env node
/**
 * Checks the print typography scale declared in src/app.css.
 *
 * The check is intentionally limited to CSS font-size declarations that live inside an
 * `@media print` block, because those are CSS lengths. Inline SVG `fontSize={...}` values in
 * component files are SVG user units, not CSS points, so this script reports them separately
 * instead of treating them as pt.
 *
 * Usage: node scripts/verify-print-type-scale.mjs
 */
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'

const CSS = 'src/app.css'
const SRC = 'src'

function printBlocks(cssSource) {
  const blocks = []
  let search = 0
  while (true) {
    const start = cssSource.indexOf('@media print', search)
    if (start === -1) break
    const open = cssSource.indexOf('{', start)
    if (open === -1) break

    let depth = 0
    let close = -1
    for (let i = open; i < cssSource.length; i += 1) {
      if (cssSource[i] === '{') depth += 1
      else if (cssSource[i] === '}') {
        depth -= 1
        if (depth === 0) {
          close = i
          break
        }
      }
    }
    if (close === -1) break
    blocks.push(cssSource.slice(open + 1, close))
    search = close + 1
  }
  return blocks.join('\n')
}

function toPt(value) {
  const cleaned = value.replace(/!important/gi, '').trim()
  const match = cleaned.match(/^([\d.]+)\s*(pt|px|rem|em)$/i)
  if (!match) return null
  const number = Number(match[1])
  const unit = match[2].toLowerCase()
  if (unit === 'pt') return number
  if (unit === 'px') return number / (4 / 3)
  return number * 12 // 1rem = 16px = 12pt at the default print root size
}

const css = readFileSync(CSS, 'utf8')
const printCss = printBlocks(css)
const failures = []
const findings = []

for (const match of printCss.matchAll(/font-size\s*:\s*([^;]+);/g)) {
  const value = match[1].trim()
  const pt = toPt(value)
  if (pt === null) {
    // Custom properties such as var(...) are only an indirect size and cannot be resolved here.
    findings.push(`dynamic size: ${value}`)
    continue
  }
  findings.push(`${value} = ${pt.toFixed(1)}pt`)
  if (pt < 10) failures.push(`${value} = ${pt.toFixed(1)}pt (< 10pt)`)
}

const properties = printCss.match(/--setubiz-print-fs-[a-z-]+\s*:/g) ?? []
if (properties.length < 8) {
  failures.push(`shared scale defines only ${properties.length} sizes; expected at least 8`)
}

const inlineSvgFindings = []
function walk(dir) {
  return readdirSync(dir).flatMap((entry) => {
    const path = join(dir, entry)
    return statSync(path).isDirectory() ? walk(path) : /\.tsx$/.test(path) ? [path] : []
  })
}
for (const file of walk(SRC)) {
  const source = readFileSync(file, 'utf8')
  const lines = source.split('\n')
  lines.forEach((line, index) => {
    for (const match of line.matchAll(/fontSize\s*=\s*\{([^}]+)\}/g)) {
      // SVG presentation attributes are user units; report them for Task E review without
      // converting their numbers to CSS points.
      inlineSvgFindings.push(`${file}:${index + 1} fontSize={${match[1].trim()}}`)
    }
  })
}

console.log(`Inspected ${CSS} print blocks`)
console.log(`Shared print size properties: ${properties.length}`)
console.log(`Print font-size declarations: ${findings.length}`)

if (findings.length > 0) {
  console.log('Print font declarations:')
  for (const finding of findings) console.log(`  ${finding}`)
}

if (inlineSvgFindings.length > 0) {
  console.log('Inline SVG fontSize attributes (SVG user units; not CSS points):')
  for (const finding of inlineSvgFindings) console.log(`  ${finding}`)
}

if (failures.length > 0) {
  console.error('Print type scale check failed:')
  for (const failure of failures) console.error(`  ${failure}`)
  process.exit(1)
}

console.log('Print type scale check passed.')
