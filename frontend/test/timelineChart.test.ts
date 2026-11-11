import { describe, expect, it } from 'vitest'
import type { TimelineDataPoint } from '../shared/types/timeline'
import {
  buildTimelineModel,
  chooseAxisMax,
  formatTimelineBucketTitle,
  formatDayLandmark,
  getDayBoundaries,
  getTimelineTickFormat,
  getBucketEnd,
  getTimelineBucketDisplayRange,
  getTimelineBucketVisibleRange,
  niceCeil,
  pickClippedLabels,
  pickTimeFrame,
} from '../app/utils/timelineChart'

const MINUTE = 60 * 1000
const HOUR = 60 * MINUTE
const DAY = 24 * HOUR
const START = Date.UTC(2026, 10, 10, 12)

const hourly = (counts: number[]): TimelineDataPoint[] =>
  counts.map((total, index) => ({ timestamp: new Date(START + index * HOUR).toISOString(), total }))

const model = (points: TimelineDataPoint[], frame = '1h' as const, now = START + 100 * DAY) =>
  buildTimelineModel(points, { frame, windowStart: START, windowEnd: START + points.length * HOUR, now })

describe('pickTimeFrame', () => {
  it.each([
    [30 * MINUTE, '1m'],
    [2 * HOUR, '5m'],
    [6 * HOUR, '15m'],
    [24 * HOUR, '1h'],
    [7 * DAY, '3h'],
    [14 * DAY, '6h'],
    [30 * DAY, '12h'],
    [60 * DAY, '1d'],
    [90 * DAY, '1w'],
    [5 * 365 * DAY, '1w'],
  ])('uses the finest size for a range of %d ms that fits the bar budget', (range, frame) => {
    expect(pickTimeFrame(range)).toBe(frame)
  })

  it('never offers more bars than the budget below the coarsest size', () => {
    for (let hours = 1; hours <= 24 * 60; hours += 7) {
      const frame = pickTimeFrame(hours * HOUR)
      if (frame !== '1w') expect(Math.ceil((hours * HOUR) / getBucketEnd(0, frame))).toBeLessThanOrEqual(60)
    }
  })
})

describe('getBucketEnd', () => {
  it('adds the fixed length for sub-day sizes', () => {
    expect(getBucketEnd(START, '15m')).toBe(START + 15 * MINUTE)
    expect(getBucketEnd(START, '12h')).toBe(START + 12 * HOUR)
  })

  it('counts days on the local calendar', () => {
    const start = new Date(2026, 2, 28).getTime() // local midnight
    const end = getBucketEnd(start, '1d')
    expect(new Date(end).getDate()).toBe(29)
    expect(new Date(end).getHours()).toBe(0)
  })

  it('ends a week seven local days later', () => {
    const start = new Date(2026, 10, 9).getTime()
    expect(new Date(getBucketEnd(start, '1w')).getDate()).toBe(16)
  })
})

describe('bucket ranges', () => {
  it('returns the complete bucket inside the window', () => {
    expect(getTimelineBucketVisibleRange(9 * HOUR, 10 * HOUR, 8 * HOUR, 11 * HOUR)).toEqual({ start: 9 * HOUR, end: 10 * HOUR })
  })

  it('clips a bucket to the window boundaries', () => {
    expect(getTimelineBucketVisibleRange(9 * HOUR, 10 * HOUR, 9.25 * HOUR, 9.75 * HOUR)).toEqual({ start: 9.25 * HOUR, end: 9.75 * HOUR })
  })

  it('makes a natural bucket end inclusive for display', () => {
    expect(getTimelineBucketDisplayRange(9 * HOUR, 10 * HOUR, 8 * HOUR, 11 * HOUR)).toEqual({ start: 9 * HOUR, end: 10 * HOUR - 1 })
  })

  it('keeps an explicit partial-window end', () => {
    expect(getTimelineBucketDisplayRange(9 * HOUR, 10 * HOUR, 9.25 * HOUR, 9.75 * HOUR)).toEqual({ start: 9.25 * HOUR, end: 9.75 * HOUR })
  })
})

describe('niceCeil', () => {
  it.each([[0, 1], [7, 10], [11, 20], [21, 25], [26, 50], [51, 100], [1234, 2000]])('rounds %d up to %d', (value, expected) => {
    expect(niceCeil(value)).toBe(expected)
  })
})

describe('chooseAxisMax', () => {
  it('keeps a linear axis for ordinary spread', () => {
    expect(chooseAxisMax([3, 8, 12, 25, 6, 5, 11, 31, 26, 4])).toBeUndefined()
  })

  it('caps the axis when one burst dwarfs the rest', () => {
    // 75th percentile 80 -> cap 200 (round above 1.5 x 80); the burst is far beyond four times that.
    expect(chooseAxisMax([40, 60, 90, 50, 70, 45, 80, 55, 168000])).toBe(200)
  })

  it('does not cap a moderate peak', () => {
    expect(chooseAxisMax([40, 60, 90, 50, 70, 45, 80, 55, 300])).toBeUndefined()
  })

  it('leaves too few points alone', () => {
    expect(chooseAxisMax([1, 2, 100000])).toBeUndefined()
  })
})

describe('buildTimelineModel data situations', () => {
  it('handles an empty response', () => {
    const empty = model([])
    expect(empty.bars).toEqual([])
    expect(empty.xRange).toEqual({ min: START, max: START })
  })

  it('handles a single bucket', () => {
    const single = model(hourly([5]))
    expect(single.bars).toHaveLength(1)
    expect(single.xRange).toEqual({ min: START - 30 * MINUTE, max: START + 30 * MINUTE })
  })

  it('draws nothing for zero and lifts a count of one so it stays visible', () => {
    const sparse = model(hourly([0, 1, 0, 1000, 0, 0]))
    const [zero, one, , big] = sparse.bars
    expect(zero!.plotY).toBe(0)
    expect(one!.plotY).toBeCloseTo(1000 * 0.02)
    expect(one!.y).toBe(1)
    expect(big!.plotY).toBe(1000)
  })

  it('keeps constant data on one scale', () => {
    const constant = model(hourly(Array.from({ length: 24 }, () => 7)))
    expect(constant.yMax).toBeUndefined()
    expect(constant.capped).toBe(false)
    expect(constant.bars.every(bar => bar.plotY === 7)).toBe(true)
  })

  it('gives all-zero data a fixed small axis', () => {
    expect(model(hourly([0, 0, 0, 0])).yMax).toBe(4)
  })

  it('clips a burst to the cap and keeps its real count', () => {
    const spiky = model(hourly([40, 60, 90, 50, 70, 45, 80, 55, 168000, 60, 40]))
    const burst = spiky.bars[8]!
    expect(spiky.capped).toBe(true)
    expect(spiky.yMax).toBe(200)
    expect(burst.clipped).toBe(true)
    expect(burst.plotY).toBe(200)
    expect(burst.y).toBe(168000)
    expect(spiky.bars[0]!.clipped).toBe(false)
  })

  it('keeps two far apart buckets as given', () => {
    const far = buildTimelineModel(
      [
        { timestamp: new Date(START).toISOString(), total: 4 },
        { timestamp: new Date(START + 40 * DAY).toISOString(), total: 9 },
      ],
      { frame: '1d', windowStart: START, windowEnd: START + 41 * DAY, now: START + 100 * DAY },
    )
    expect(far.bars.map(bar => bar.y)).toEqual([4, 9])
    expect(far.xRange.min).toBeLessThan(START)
  })

  it('marks only the bucket that has not ended yet', () => {
    const points = hourly([1, 2, 3])
    const running = model(points, '1h', START + 2 * HOUR + 10 * MINUTE)
    expect(running.bars.map(bar => bar.running)).toEqual([false, false, true])
  })
})

describe('axis labels', () => {
  it('uses clock times for a short range and dates for days, weeks and long ranges', () => {
    expect(getTimelineTickFormat('1h', DAY)).toBe('HH:mm')
    expect(getTimelineTickFormat('15m', 3 * DAY)).toBe('HH:mm')
    expect(getTimelineTickFormat('3h', 7 * DAY)).toBe('dd MMM')
    expect(getTimelineTickFormat('1d', 30 * DAY)).toBe('dd MMM')
    expect(getTimelineTickFormat('1w', 90 * DAY)).toBe('dd MMM')
  })

  it('finds the local midnights inside the axis', () => {
    const min = new Date(2026, 10, 10, 14).getTime()
    const max = new Date(2026, 10, 12, 3).getTime()
    expect(getDayBoundaries(min, max)).toEqual([new Date(2026, 10, 11).getTime(), new Date(2026, 10, 12).getTime()])
  })

  it('finds none inside a single day', () => {
    expect(getDayBoundaries(new Date(2026, 10, 10, 1).getTime(), new Date(2026, 10, 10, 23).getTime())).toEqual([])
  })

  it('names a landmark by day and month', () => {
    expect(formatDayLandmark(new Date(2026, 10, 11).getTime())).toBe('11 Nov')
  })
})

describe('formatTimelineBucketTitle', () => {
  // Local times: the title is shown in the viewer's zone.
  const noon = new Date(2026, 10, 10, 12).getTime()
  const window = { start: noon - 100 * DAY, end: noon + 100 * DAY }
  const bar = { bucketStart: noon, bucketEnd: noon + HOUR, running: false }

  it('shows the hour range of an hourly bucket', () => {
    expect(formatTimelineBucketTitle(bar, '1h', window)).toBe('10 Nov, 12:00–12:59')
  })

  it('shows a single time for one-minute buckets', () => {
    expect(formatTimelineBucketTitle({ ...bar, bucketEnd: noon + MINUTE }, '1m', window)).toBe('10 Nov, 12:00')
  })

  it('shows the date for a day bucket', () => {
    const day = new Date(2026, 10, 10).getTime()
    expect(formatTimelineBucketTitle({ bucketStart: day, bucketEnd: getBucketEnd(day, '1d'), running: false }, '1d', window)).toBe('10 Nov 2026')
  })

  it('cuts the bucket to the selected window and flags a running bucket', () => {
    const cut = { start: noon + 15 * MINUTE, end: noon + 40 * MINUTE }
    expect(formatTimelineBucketTitle({ ...bar, running: true }, '1h', cut)).toBe('10 Nov, 12:15–12:40 · in progress')
  })
})

const bar = (y: number, clipped = true) => ({ x: 0, bucketStart: 0, bucketEnd: 1, y, plotY: 1, clipped, running: false })

describe('pickClippedLabels', () => {
  it('labels every clipped bar when there is room', () => {
    const bars = [bar(900), bar(1, false), bar(1, false), bar(1, false), bar(1, false), bar(1, false), bar(1, false), bar(1, false), bar(1, false), bar(800)]
    expect(pickClippedLabels(bars).map(b => b.y)).toEqual([900, 800])
  })

  it('keeps the highest of neighbouring bursts and skips the ones it would cover', () => {
    const bars = Array.from({ length: 31 }, () => bar(1, false))
    bars[10] = bar(33000)
    bars[11] = bar(168000)
    bars[12] = bar(101000)
    expect(pickClippedLabels(bars).map(b => b.y)).toEqual([168000])
  })

  it('gives nothing without clipped bars', () => {
    expect(pickClippedLabels([bar(3, false), bar(4, false)])).toEqual([])
  })
})
