export interface TimelineDataPoint {
  timestamp: string
  total: number
}

export type TimeFrame = 'minute' | 'hour' | 'day' | 'week'

export interface TimelineResponse {
  time_frame: TimeFrame
  start_date: string
  end_date: string
  data: TimelineDataPoint[]
}
