import { describe, expect, it } from 'vitest'
import {
  getTimelineBucketDisplayRange,
  getTimelineBucketVisibleRange,
  getTimelineXAxisRange,
  renderTimelineTooltip,
} from '../app/utils/timelineChart'

const HOUR = 60 * 60 * 1000
const DAY = 24 * HOUR

describe('getTimelineXAxisRange', () => {
  it('uses the selected range when there is no data', () => {
    expect(getTimelineXAxisRange([], 0, 24 * HOUR, 'hour')).toEqual({ min: 0, max: 24 * HOUR })
  })

  it('leaves half a bucket on each side of the bars', () => {
    expect(getTimelineXAxisRange([9 * HOUR, 10 * HOUR, 11 * HOUR], 0, 24 * HOUR, 'hour')).toEqual({
      min: 8.5 * HOUR,
      max: 11.5 * HOUR,
    })
  })

  it('scales the padding with the bucket size', () => {
    expect(getTimelineXAxisRange([3 * DAY], 0, 9 * DAY, 'day')).toEqual({
      min: 2.5 * DAY,
      max: 3.5 * DAY,
    })
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


describe('renderTimelineTooltip', () => {
  it('shows the bucket title and the count with Apex tooltip classes', () => {
    const html = renderTimelineTooltip('10 Nov, 21:00–21:59', 11, '#d33')

    expect(html).toContain('apexcharts-tooltip-title')
    expect(html).toContain('10 Nov, 21:00–21:59')
    expect(html).toContain('11 alerts')
    expect(html).toContain('#d33')
  })

  it('uses the singular for one alert', () => {
    expect(renderTimelineTooltip('t', 1, '#d33')).toContain('>1 alert<')
  })
})
