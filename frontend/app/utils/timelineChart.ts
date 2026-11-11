import type { TimeFrame } from '../../shared/types/timeline'

const HOUR = 60 * 60 * 1000
const DAY = 24 * HOUR

const BUCKET_DURATION: Record<TimeFrame, number> = {
  minute: 60 * 1000,
  hour: HOUR,
  day: DAY,
  week: 7 * DAY,
}

function getBucketEnd(bucketStart: number, timeFrame: TimeFrame): number {
  return bucketStart + BUCKET_DURATION[timeFrame]
}

export function getTimelineBucketVisibleRange(
  bucketStart: number,
  fullStart: number,
  fullEnd: number,
  timeFrame: TimeFrame,
) {
  const bucketEnd = getBucketEnd(bucketStart, timeFrame)
  const start = Math.max(bucketStart, fullStart)
  const end = Math.min(bucketEnd, fullEnd)

  return end > start ? { start, end } : { start: bucketStart, end: bucketEnd }
}

export function getTimelineBucketDisplayRange(
  bucketStart: number,
  fullStart: number,
  fullEnd: number,
  timeFrame: TimeFrame,
) {
  const range = getTimelineBucketVisibleRange(bucketStart, fullStart, fullEnd, timeFrame)
  const bucketEnd = getBucketEnd(bucketStart, timeFrame)
  const end = range.end === bucketEnd ? range.end - 1 : range.end
  return { start: range.start, end: Math.max(range.start, end) }
}

/**
 * Axis limits for bars drawn at their bucket start: half a bucket on each side,
 * so the first and last bar are not cut off. Without data the selected range shows.
 */
export function getTimelineXAxisRange(
  bucketStarts: number[],
  fullStart: number,
  fullEnd: number,
  timeFrame: TimeFrame,
) {
  if (bucketStarts.length === 0) return { min: fullStart, max: fullEnd }

  const half = BUCKET_DURATION[timeFrame] / 2
  return {
    min: Math.min(...bucketStarts) - half,
    max: Math.max(...bucketStarts) + half,
  }
}

/**
 * Tooltip body for one bar, in the markup and classes Apex uses itself so its tooltip theme applies.
 *
 * It replaces `tooltip.x.formatter`: with Apex 8 any `tooltip.x` setting enables the x-axis tooltip,
 * which shortens the column highlight (crosshair) to about half the plot height.
 * `title` is formatted dates only; `color` comes from the design tokens.
 */
export function renderTimelineTooltip(title: string, count: number, color: string): string {
  const label = `${count} alert${count !== 1 ? 's' : ''}`
  return (
    `<div class="apexcharts-tooltip-title" style="font-family: inherit; font-size: 12px;">${title}</div>` +
    '<div class="apexcharts-tooltip-series-group apexcharts-active" style="order: 1; display: flex;">' +
    `<span class="apexcharts-tooltip-marker" shape="circle" style="background-color: ${color}; color: ${color};"></span>` +
    '<div class="apexcharts-tooltip-text" style="font-family: inherit; font-size: 12px;">' +
    '<div class="apexcharts-tooltip-y-group">' +
    '<span class="apexcharts-tooltip-text-y-label">Alerts: </span>' +
    `<span class="apexcharts-tooltip-text-y-value">${label}</span>` +
    '</div></div></div>'
  )
}
