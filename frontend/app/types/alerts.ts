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
  total_alerts: number
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

// Additional types for alert details
export interface WebServiceInfo {
  url?: string
  cgi?: string
  http_method?: string
}

export interface AlertIdentInfo {
  alertident?: string
  analyzerid?: string
}

export interface ReferenceInfo {
  origin?: string
  name?: string
  url?: string
  meaning?: string
}

export interface ServiceInfo {
  port?: number
  protocol?: string
  direction: string
  ip_version?: number
  name?: string
  iana_protocol_number?: number
  iana_protocol_name?: string
  portlist?: string
  ident?: string
}

export interface NetworkInfo {
  interface?: string
  category?: string
  address?: string
  netmask?: string
  vlan_name?: string
  vlan_num?: number
  ident?: string
  ip_version?: number
  ip_hlen?: number
  protocol?: string
  protocol_number?: number
  node?: NodeInfo
  heartbeat_process?: ProcessInfo
  addresses: string[]
}

// Comprehensive alert detail from backend
export interface AlertDetail {
  id: string
  message_id: string
  created_at?: TimeInfo
  detected_at: TimeInfo
  classification_text?: string
  classification_ident?: string
  severity?: string
  description?: string
  completion?: string
  impact_type?: string
  source?: NetworkInfo
  target?: NetworkInfo
  analyzers: AnalyzerInfo[]
  references: ReferenceInfo[]
  services: ServiceInfo[]
  web_services: WebServiceInfo[]
  alert_idents: AlertIdentInfo[]
  additional_data: Record<string, any>
}