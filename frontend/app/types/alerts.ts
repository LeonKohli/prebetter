// Alert types matching backend schemas

export interface TimeInfo {
  timestamp: string
  usec?: number
  gmtoff?: number
}

export interface NodeInfo {
  name?: string
  location?: string
  category?: string
  ident?: string
  address?: string
  os?: string
  agents_count?: number
}

export interface ProcessInfo {
  name?: string
  pid?: number
  path?: string
  args: string[]
  env: string[]
}

export interface AnalyzerInfo {
  name: string
  analyzer_id?: string
  node?: NodeInfo
  model?: string
  manufacturer?: string
  version?: string
  class_type?: string
  ostype?: string
  osversion?: string
  process?: ProcessInfo
  analyzer_time?: TimeInfo
  chain_index?: number
  role?: string
}

export interface AlertListItem {
  id: string
  message_id: string
  created_at?: TimeInfo
  detected_at: TimeInfo
  classification_text?: string
  severity?: string
  source_ipv4?: string
  target_ipv4?: string
  analyzer?: AnalyzerInfo
}

export interface GroupedAlertDetail {
  classification: string
  count: number
  analyzer: string[]
  analyzer_host: string[]
  detected_at: string
}

export interface GroupedAlert {
  source_ipv4?: string
  target_ipv4?: string
  total_count: number
  alerts: GroupedAlertDetail[]
}

export interface PaginatedResponse {
  total: number
  page: number
  size: number
  pages: number
}

export interface AlertListResponse {
  items: AlertListItem[]
  pagination: PaginatedResponse
}

export interface GroupedAlertResponse {
  groups: GroupedAlert[]
  pagination: PaginatedResponse
}

// Flattened representation of grouped alerts for table display
export interface FlattenedGroupedAlert extends GroupedAlertDetail {
  source_ipv4?: string
  target_ipv4?: string
  total_count: number
  groupIndex: number
  alertIndex: number
  isFirstInGroup: boolean
  isLastInGroup: boolean
  groupSize: number
}