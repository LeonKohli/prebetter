export interface TimelineDataPoint {
  timestamp: string
  total: number
  by_severity: Record<string, number>
  by_classification: Record<string, number>
  by_analyzer: Record<string, number>
}

export type TimeFrame = 'hour' | 'day' | 'week' | 'month'

export interface TimelineResponse {
  time_frame: TimeFrame
  start_date: string
  end_date: string
  data: TimelineDataPoint[]
}
