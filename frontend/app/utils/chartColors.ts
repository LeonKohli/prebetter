import { formatHex, parse } from 'culori'

export function getChartColor(index: 1 | 2 | 3 | 4 | 5 = 1, fallback = '#6366f1'): string {
  if (typeof document === 'undefined') return fallback

  const varName = `--color-chart-${index}`
  const computed = getComputedStyle(document.documentElement).getPropertyValue(varName).trim()

  if (!computed) return fallback

  const parsed = parse(computed)
  if (!parsed) return fallback

  return formatHex(parsed) ?? fallback
}
