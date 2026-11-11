import type { TimeFrame, TimelineDataPoint } from '../../shared/types/timeline'

const MINUTE = 60 * 1000
const HOUR = 60 * MINUTE
const DAY = 24 * HOUR

/** Bucket sizes the server offers, finest first. Day and week are nominal lengths (calendar units). */
export const TIME_FRAMES: { frame: TimeFrame, ms: number }[] = [
  { frame: '1m', ms: MINUTE },
  { frame: '5m', ms: 5 * MINUTE },
  { frame: '15m', ms: 15 * MINUTE },
  { frame: '1h', ms: HOUR },
  { frame: '3h', ms: 3 * HOUR },
  { frame: '6h', ms: 6 * HOUR },
  { frame: '12h', ms: 12 * HOUR },
  { frame: '1d', ms: DAY },
  { frame: '1w', ms: 7 * DAY },
]

/**
 * Bars a chart of this width reads well with. Kibana aims for 50 (histogram:barTarget), Splunk
 * caps at 100, Datadog shows 60 to 180: below this the bars are still at least ~20 px wide.
 */
export const MAX_BARS = 60

/** Finest bucket size that keeps the range at or under `maxBars` bars; weeks when nothing does. */
export function pickTimeFrame(rangeMs: number, maxBars = MAX_BARS): TimeFrame {
  const fit = TIME_FRAMES.find(({ ms }) => Math.ceil(rangeMs / ms) <= maxBars)
  return (fit ?? TIME_FRAMES[TIME_FRAMES.length - 1]!).frame
}

/** End (exclusive) of the bucket starting at `start`. Days and weeks are counted on the local calendar. */
export function getBucketEnd(start: number, frame: TimeFrame): number {
  if (frame === '1d' || frame === '1w') {
    const end = new Date(start)
    end.setDate(end.getDate() + (frame === '1w' ? 7 : 1))
    return end.getTime()
  }
  return start + TIME_FRAMES.find(item => item.frame === frame)!.ms
}

export function getTimelineBucketVisibleRange(bucketStart: number, bucketEnd: number, fullStart: number, fullEnd: number) {
  const start = Math.max(bucketStart, fullStart)
  const end = Math.min(bucketEnd, fullEnd)

  return end > start ? { start, end } : { start: bucketStart, end: bucketEnd }
}

/** Range a tooltip or a bar click covers: the bucket cut to the selected window, end inclusive. */
export function getTimelineBucketDisplayRange(bucketStart: number, bucketEnd: number, fullStart: number, fullEnd: number) {
  const range = getTimelineBucketVisibleRange(bucketStart, bucketEnd, fullStart, fullEnd)
  const end = range.end === bucketEnd ? range.end - 1 : range.end
  return { start: range.start, end: Math.max(range.start, end) }
}

export interface TimelineBar {
  /** Bucket start, where the bar and its label sit. */
  x: number
  bucketStart: number
  bucketEnd: number
  /** Real count. */
  y: number
  /** Height drawn: the count, lifted to stay visible, or the axis cap for an outlier. */
  plotY: number
  /** The count is above the capped axis. */
  clipped: boolean
  /** The bucket has not ended yet, so its count is still growing. */
  running: boolean
}

export interface TimelineModel {
  bars: TimelineBar[]
  /** Fixed upper end of the y-axis, or undefined to let the chart choose. */
  yMax: number | undefined
  /** An outlier made the axis stop below the highest bar. */
  capped: boolean
  xRange: { min: number, max: number }
}

/** Smallest of 1, 2, 2.5, 5, 10 times a power of ten that is at least `value`. */
export function niceCeil(value: number): number {
  if (value <= 0) return 1
  const magnitude = 10 ** Math.floor(Math.log10(value))
  const step = [1, 2, 2.5, 5, 10].find(candidate => candidate * magnitude >= value)!
  return step * magnitude
}

/**
 * Axis maximum for counts with a dominant outlier, or undefined when the data fits one scale.
 *
 * On a linear axis one burst of 170 000 next to hours of 50 flattens everything else below a
 * pixel. The axis then stops at a round value above the typical peak (the 75th percentile with
 * some room; a higher percentile would contain the outlier itself in a short series) and the
 * outlier runs off the top, marked and labelled with its real count. Only a clear outlier, more
 * than four times that cap, triggers this; ordinary spread keeps a linear axis.
 */
export function chooseAxisMax(counts: number[]): number | undefined {
  const sorted = counts.filter(count => count > 0).sort((a, b) => a - b)
  if (sorted.length < 5) return undefined

  const peak = sorted[sorted.length - 1]!
  const typical = sorted[Math.max(0, Math.ceil(sorted.length * 0.75) - 1)]!
  const cap = niceCeil(Math.max(typical * 1.5, 10))
  return peak > cap * 4 ? cap : undefined
}

/** Share of the axis a non-zero bar always keeps, about 2 px on a 100 px plot. */
const MIN_VISIBLE_SHARE = 0.02

export function buildTimelineModel(
  points: TimelineDataPoint[],
  options: { frame: TimeFrame, windowStart: number, windowEnd: number, now: number },
): TimelineModel {
  const { frame, windowStart, windowEnd, now } = options
  const counts = points.map(point => point.total)
  const cap = chooseAxisMax(counts)
  const axisMax = cap ?? Math.max(...counts, 0)

  const bars = points
    .map((point): TimelineBar | undefined => {
      const bucketStart = Date.parse(point.timestamp)
      if (!Number.isFinite(bucketStart)) return undefined
      const bucketEnd = getBucketEnd(bucketStart, frame)
      const clipped = cap !== undefined && point.total > cap
      const plotY = clipped
        ? cap
        : point.total > 0 ? Math.max(point.total, axisMax * MIN_VISIBLE_SHARE) : 0
      return { x: bucketStart, bucketStart, bucketEnd, y: point.total, plotY, clipped, running: bucketEnd > now && bucketStart <= now }
    })
    .filter(bar => bar !== undefined)

  const first = bars[0]
  const last = bars[bars.length - 1]
  return {
    bars,
    yMax: cap ?? (axisMax === 0 ? 4 : undefined),
    capped: cap !== undefined && bars.some(bar => bar.clipped),
    // Half a bucket on each side keeps the first and last bar whole.
    xRange: first && last
      ? {
          min: first.bucketStart - (first.bucketEnd - first.bucketStart) / 2,
          max: last.bucketStart + (last.bucketEnd - last.bucketStart) / 2,
        }
      : { min: windowStart, max: windowEnd },
  }
}

const dayMonth = new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short' })
const clock = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })

/**
 * Apex date format of the axis labels. It has to be a `format` string: with a `formatter`
 * function Apex spreads the ticks evenly over the axis instead of placing them on round times,
 * and the labels drift away from their bars.
 */
export function getTimelineTickFormat(frame: TimeFrame, rangeMs: number): string {
  // Clock times name a day only through landmarks, which stop being readable after a few days.
  return frame === '1d' || frame === '1w' || rangeMs > 3 * DAY ? 'dd MMM' : 'HH:mm'
}

/** Local midnights inside the axis: the day landmarks of a chart whose labels are clock times. */
export function getDayBoundaries(min: number, max: number): number[] {
  const boundaries: number[] = []
  const day = new Date(min)
  day.setHours(24, 0, 0, 0)
  while (day.getTime() < max) {
    boundaries.push(day.getTime())
    day.setDate(day.getDate() + 1)
  }
  return boundaries
}

/** Label of a day landmark. */
export function formatDayLandmark(timestamp: number): string {
  return dayMonth.format(timestamp)
}

const dateTime = new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
const dayMonthYear = new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })

/** Tooltip heading of a bar: the bucket cut to the selected window; a bucket that has not ended says so. */
export function formatTimelineBucketTitle(
  bar: Pick<TimelineBar, 'bucketStart' | 'bucketEnd' | 'running'>,
  frame: TimeFrame,
  window: { start: number, end: number },
): string {
  const { start, end } = getTimelineBucketDisplayRange(bar.bucketStart, bar.bucketEnd, window.start, window.end)
  let title: string
  if (frame === '1m') {
    title = dateTime.format(start)
  }
  else if (frame === '1d' || frame === '1w') {
    const first = dayMonthYear.format(start)
    const last = dayMonthYear.format(end)
    title = first === last ? first : `${first}–${last}`
  }
  else {
    const sameDay = dayMonthYear.format(start) === dayMonthYear.format(end)
    title = `${dateTime.format(start)}–${sameDay ? clock.format(end) : dateTime.format(end)}`
  }
  return bar.running ? `${title} · in progress` : title
}

/**
 * Clipped bars that get a count label: the highest first, and only where the labels do not
 * overlap. Neighbouring bursts would otherwise print on top of each other; the tooltip still
 * gives every count. `plotWidth` is an estimate in px, `labelWidth` the room one label needs.
 */
export function pickClippedLabels(bars: TimelineBar[], plotWidth = 1200, labelWidth = 56): TimelineBar[] {
  const slot = plotWidth / Math.max(bars.length, 1)
  const minGap = Math.max(1, Math.ceil(labelWidth / slot))
  const picked: number[] = []
  const ranked = bars
    .map((bar, index) => ({ bar, index }))
    .filter(({ bar }) => bar.clipped)
    .sort((a, b) => b.bar.y - a.bar.y)

  for (const { index } of ranked) {
    if (picked.every(other => Math.abs(other - index) >= minGap)) picked.push(index)
  }
  return picked.sort((a, b) => a - b).map(index => bars[index]!)
}
