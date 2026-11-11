import type { TimeFrame } from '../../shared/types/timeline'

const HOUR = 60 * 60 * 1000
const DAY = 24 * HOUR

const BUCKET_DURATION: Record<TimeFrame, number> = {
  minute: 60 * 1000,
  hour: HOUR,
  day: DAY,
  week: 7 * DAY,
}

export function getTimelineBucketDuration(bucketStart: number, timeFrame: TimeFrame): number {
  return getBucketEnd(bucketStart, timeFrame) - bucketStart
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

export function getTimelineBucketPlotTimestamp(
  bucketStart: number,
  fullStart: number,
  fullEnd: number,
  timeFrame: TimeFrame,
) {
  const { start, end } = getTimelineBucketVisibleRange(bucketStart, fullStart, fullEnd, timeFrame)
  return start + (end - start) / 2
}

export function getTimelineXAxisRange(
  timestamps: number[],
  fullStart: number,
  fullEnd: number,
  timeFrame: TimeFrame,
) {
  if (timestamps.length === 0) return { min: fullStart, max: fullEnd }

  const dataMin = Math.min(...timestamps)
  const dataMax = Math.max(...timestamps)
  const bucketDuration = BUCKET_DURATION[timeFrame]

  if (timestamps.length === 1) {
    const padding = bucketDuration * 2
    return {
      min: Math.min(dataMin, Math.max(fullStart, dataMin - padding)),
      max: Math.min(fullEnd, dataMax + padding),
    }
  }

  const dataSpan = dataMax - dataMin
  const padding = Math.max(bucketDuration, dataSpan * 0.25)

  return {
    min: Math.max(fullStart, dataMin - padding),
    max: Math.min(fullEnd, dataMax + padding),
  }
}

export function getTimelineColumnWidth(
  timestamps: number[],
  bucketDuration: number,
): string | number {
  if (timestamps.length <= 1) return 12

  const sorted = [...new Set(timestamps)].sort((a, b) => a - b)
  const gaps = sorted.slice(1).map((timestamp, index) => timestamp - sorted[index]!)
  const minimumGap = Math.min(...gaps.filter(gap => gap > 0))
  if (!Number.isFinite(minimumGap)) return 12

  const percentage = Math.round((bucketDuration / minimumGap) * 80)
  return `${Math.min(80, Math.max(4, percentage))}%`
}

export type TimelineReference = 'off' | 'average' | 'median' | 'p95'

export const TIMELINE_REFERENCES: { value: TimelineReference; label: string }[] = [
  { value: 'off', label: 'No reference' },
  { value: 'average', label: 'Average' },
  { value: 'median', label: 'Median' },
  { value: 'p95', label: '95th percentile' },
]

/**
 * Value of the reference line over the buckets of the window. Empty buckets
 * are part of the series (they arrive as 0), so quiet periods count.
 * The 95th percentile uses the nearest-rank method.
 */
export function getTimelineReferenceValue(
  values: number[],
  reference: TimelineReference,
): number | null {
  if (reference === 'off' || values.length === 0) return null

  if (reference === 'average') {
    return values.reduce((sum, value) => sum + value, 0) / values.length
  }

  const sorted = [...values].sort((a, b) => a - b)
  if (reference === 'p95') {
    return sorted[Math.max(0, Math.ceil(sorted.length * 0.95) - 1)]!
  }

  const middle = Math.floor(sorted.length / 2)
  return sorted.length % 2 ? sorted[middle]! : (sorted[middle - 1]! + sorted[middle]!) / 2
}

export function formatTimelineReference(value: number, reference: TimelineReference): string {
  const rounded = Number.isInteger(value) ? String(value) : value.toFixed(1)
  const name = { off: '', average: 'Avg', median: 'Median', p95: 'P95' }[reference]
  return `${name} ${rounded}`
}
