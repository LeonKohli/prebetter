export interface TimelineDataPoint {
  timestamp: string
  total: number
}

/** Typical range of one hour, from the same hour of earlier weeks (hourly buckets only). */
export interface TimelineBaselinePoint {
  timestamp: string
  low: number
  high: number
  typical: number
}

export type TimeFrame = 'minute' | 'hour' | 'day' | 'week'

export interface TimelineResponse {
  time_frame: TimeFrame
  start_date: string
  end_date: string
  data: TimelineDataPoint[]
  baseline: TimelineBaselinePoint[]
}
