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
