import { formatHex, parse, useMode, modeOklch, modeRgb } from 'culori/fn'

// Register only the modes we need: oklch for parsing CSS custom properties,
// rgb for formatHex conversion. Drops culori bundle from ~23.7KB to ~2-4KB gzipped.
useMode(modeOklch)
useMode(modeRgb)

export function getChartColor(index: 1 | 2 | 3 | 4 | 5 = 1, fallback = '#6366f1'): string {
  if (typeof document === 'undefined') return fallback

  // Use --chart-* (defined in :root) not --color-chart-* (only available at Tailwind build time via @theme inline)
  const varName = `--chart-${index}`
  const computed = getComputedStyle(document.documentElement).getPropertyValue(varName).trim()

  if (!computed) return fallback

  const parsed = parse(computed)
  if (!parsed) return fallback

  return formatHex(parsed) ?? fallback
}
