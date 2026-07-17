import { describe, expect, it } from 'vitest'
import {
  getTimelineBucketDisplayRange,
  getTimelineBucketPlotTimestamp,
  getTimelineBucketVisibleRange,
  getTimelineColumnWidth,
  getTimelineXAxisRange,
} from '@/utils/timelineChart'

const HOUR = 60 * 60 * 1000
const MINUTE = 60 * 1000
const DAY = 24 * HOUR

describe('getTimelineXAxisRange', () => {
  it('uses the selected range when there is no data', () => {
    expect(getTimelineXAxisRange([], 0, 24 * HOUR, 'hour')).toEqual({
      min: 0,
      max: 24 * HOUR,
    })
  })

  it('centers one point with two buckets of padding', () => {
    expect(getTimelineXAxisRange([12 * HOUR], 0, 24 * HOUR, 'hour')).toEqual({
      min: 10 * HOUR,
      max: 14 * HOUR,
    })
  })

  it('does not expand a sparse series before the selected range', () => {
    expect(getTimelineXAxisRange([8 * HOUR, 9 * HOUR], 7.9 * HOUR, 9.9 * HOUR, 'hour')).toEqual({
      min: 7.9 * HOUR,
      max: 9.9 * HOUR,
    })
  })

  it('keeps a leading partial bucket inside the selected range', () => {
    const firstPoint = getTimelineBucketPlotTimestamp(9 * HOUR, 9.5 * HOUR, 12 * HOUR, 'hour')
    const secondPoint = getTimelineBucketPlotTimestamp(10 * HOUR, 9.5 * HOUR, 12 * HOUR, 'hour')

    expect(getTimelineXAxisRange([firstPoint, secondPoint], 9.5 * HOUR, 12 * HOUR, 'hour')).toEqual({
      min: 9.5 * HOUR,
      max: 11.5 * HOUR,
    })
  })

  it('fits a dense cluster based on its time coverage, not its point count', () => {
    const timestamps = Array.from({ length: 8 }, (_, index) => (300 + index * 7) * DAY)
    const range = getTimelineXAxisRange(timestamps, 0, 365 * DAY, 'week')

    expect(range.min).toBeGreaterThan(0)
    expect(range.max).toBeLessThan(365 * DAY)
  })

  it('keeps the full range when data and padding already span it', () => {
    expect(getTimelineXAxisRange([HOUR, 23 * HOUR], 0, 24 * HOUR, 'hour')).toEqual({
      min: 0,
      max: 24 * HOUR,
    })
  })
})

describe('getTimelineBucketPlotTimestamp', () => {
  it('plots a complete bucket at its midpoint', () => {
    expect(getTimelineBucketPlotTimestamp(9 * HOUR, 8 * HOUR, 11 * HOUR, 'hour')).toBe(9.5 * HOUR)
  })

  it('centers only the visible part of the first bucket', () => {
    expect(getTimelineBucketPlotTimestamp(9 * HOUR, 9.5 * HOUR, 11 * HOUR, 'hour')).toBe(9.75 * HOUR)
  })

  it('centers only the visible part of the final bucket', () => {
    expect(getTimelineBucketPlotTimestamp(9 * HOUR, 8 * HOUR, 9.25 * HOUR, 'hour')).toBe(9.125 * HOUR)
  })
})

describe('getTimelineBucketVisibleRange', () => {
  it('returns the complete bucket inside the selected range', () => {
    expect(getTimelineBucketVisibleRange(9 * HOUR, 8 * HOUR, 11 * HOUR, 'hour')).toEqual({
      start: 9 * HOUR,
      end: 10 * HOUR,
    })
  })

  it('clips a bucket to the selected range boundaries', () => {
    expect(getTimelineBucketVisibleRange(9 * HOUR, 9.25 * HOUR, 9.75 * HOUR, 'hour')).toEqual({
      start: 9.25 * HOUR,
      end: 9.75 * HOUR,
    })
  })
})

describe('getTimelineBucketDisplayRange', () => {
  it('makes a natural bucket end inclusive for display', () => {
    expect(getTimelineBucketDisplayRange(9 * HOUR, 8 * HOUR, 11 * HOUR, 'hour')).toEqual({
      start: 9 * HOUR,
      end: 10 * HOUR - 1,
    })
  })

  it('preserves an explicit partial-range end', () => {
    expect(getTimelineBucketDisplayRange(9 * HOUR, 9.25 * HOUR, 9.75 * HOUR, 'hour')).toEqual({
      start: 9.25 * HOUR,
      end: 9.75 * HOUR,
    })
  })
})

describe('getTimelineColumnWidth', () => {
  it('keeps a single sparse bucket narrow', () => {
    expect(getTimelineColumnWidth([9 * HOUR], MINUTE)).toBe(12)
  })

  it('sizes multiple columns from bucket duration rather than sparse point spacing', () => {
    expect(getTimelineColumnWidth([9 * HOUR, 9 * HOUR + 18 * MINUTE], MINUTE)).toBe('4%')
    expect(getTimelineColumnWidth([9 * HOUR, 9 * HOUR + MINUTE], MINUTE)).toBe('80%')
  })
})
