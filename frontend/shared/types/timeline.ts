export interface TimelineDataPoint {
  timestamp: string
  total: number
}

/** Bucket size. Days and weeks follow the calendar of the time zone sent with the request. */
export type TimeFrame = '1m' | '5m' | '15m' | '1h' | '3h' | '6h' | '12h' | '1d' | '1w'

export interface TimelineResponse {
  time_frame: TimeFrame
  start_date: string
  end_date: string
  data: TimelineDataPoint[]
}
