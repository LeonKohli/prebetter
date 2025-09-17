export type HeartbeatStatus = 'active' | 'inactive' | 'offline' | 'unknown' | string

export interface HeartbeatAgent {
  name: string
  model: string
  version: string
  class: string
  latest_heartbeat_at: string | null
  seconds_ago: number
  heartbeat_interval?: number | null
  status: HeartbeatStatus
}

export interface HeartbeatNode {
  name: string
  os: string | null
  agents: HeartbeatAgent[]
}

export interface HeartbeatStatusSummary {
  [status: string]: number
}

export interface HeartbeatTreeResponse {
  nodes: HeartbeatNode[]
  total_nodes: number
  total_agents: number
  status_summary?: HeartbeatStatusSummary | null
}

export interface HeartbeatTimelineItem {
  timestamp: string
  host_name: string
  analyzer_name: string
  model: string
  version: string
  class_: string
}

export interface PaginatedHeartbeatTimelineResponse {
  items: HeartbeatTimelineItem[]
  pagination: {
    total: number
    page: number
    size: number
    pages: number
  }
}
