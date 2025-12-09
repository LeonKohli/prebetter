import { formatHex, parse } from 'culori'

/**
 * Chart color utilities for ApexCharts integration.
 *
 * ApexCharts doesn't handle OKLCH colors or CSS variables at render time,
 * so we need to read computed values and convert to hex.
 *
 * Uses culori for accurate OKLCH → hex conversion.
 */

/** Chart color CSS variable names */
export const CHART_COLORS = ['--color-chart-1', '--color-chart-2', '--color-chart-3', '--color-chart-4', '--color-chart-5'] as const

export type ChartColorVar = typeof CHART_COLORS[number]

/**
 * Get a chart color as hex from CSS variables.
 * Falls back to a default if conversion fails.
 *
 * @param index - Chart color index (1-5)
 * @param fallback - Fallback hex color if conversion fails
 */
export function getChartColor(index: 1 | 2 | 3 | 4 | 5 = 1, fallback = '#6366f1'): string {
  if (typeof document === 'undefined') return fallback

  const varName = `--color-chart-${index}`
  const computed = getComputedStyle(document.documentElement).getPropertyValue(varName).trim()

  if (!computed) return fallback

  const parsed = parse(computed)
  if (!parsed) return fallback

  return formatHex(parsed) ?? fallback
}

/**
 * Get all chart colors as hex array.
 * Useful for multi-series charts.
 */
export function getAllChartColors(): string[] {
  return [1, 2, 3, 4, 5].map(i => getChartColor(i as 1 | 2 | 3 | 4 | 5))
}
