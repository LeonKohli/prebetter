// Alert types matching backend schemas

export type Severity = 'high' | 'medium' | 'low' | 'info'

export interface TimeInfo {
  timestamp: string
}

export interface AlertListItem {
  id: string
  detected_at: TimeInfo
  classification_text?: string
  severity?: Severity | null
  source_ipv4?: string | null
  target_ipv4?: string | null
  analyzer?: { name: string }
}

export interface GroupedAlertDetail {
  classification: string
  count: number
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

export interface AlertEndpoint {
  address: string
  port?: number | null
  mac?: string | null
}

/** Header-supplied client attribution; advisory only. */
export interface ForwardedInfo {
  true_source?: string | null
  forwarded_for: string[]
  via_proxy?: string | null
}

export interface AlertDetail {
  id: string
  detected_at: TimeInfo
  severity?: Severity | null
  classification_text?: string
  rule: {
    id?: string | null
    version?: string | null
    category?: string | null
  }
  action?: string | null
  source?: AlertEndpoint | null
  target?: AlertEndpoint | null
  network: {
    transport?: string | null
    protocol?: string | null
    vlan_id?: string | null
    bytes?: number | null
    packets?: number | null
  }
  flow: {
    direction?: string | null
    started_at?: string | null
    client_bytes?: number | null
    client_packets?: number | null
    server_bytes?: number | null
    server_packets?: number | null
  }
  analyzer: {
    name?: string | null
    interface?: string | null
  }
  /** Snort's packet fields, e.g. `pkt_len`, `ip_ttl`. Which ones exist varies per alert. */
  packet: Record<string, string | number | boolean>
  /** Base64 of the bytes the rule matched on; null when the sensor did not log a payload. */
  payload?: string | null
  /** Client address from the proxied request's X-Forwarded-For header; null without one. */
  forwarded?: ForwardedInfo | null
  /** Request line (`GET /path HTTP/1.1`) from the companion document; null when there is none. */
  http_request?: string | null
  document: Record<string, unknown>
}
