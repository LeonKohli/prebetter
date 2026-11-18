import type { AlertFilters, RequestFilterField } from '../../shared/types/alerts'

/**
 * Filters on the headers of an alert's HTTP request. Each field has a list of values to show and a list to
 * hide, kept in the URL's filter object under the names the backend takes (`user_agent`, `exclude_user_agent`).
 * The helpers return new objects and leave the given one alone.
 */
export type RequestFilterMode = 'include' | 'exclude'

export const REQUEST_FILTER_FIELDS: readonly RequestFilterField[] = ['user_agent', 'host', 'client_ip']

/** The backend refuses more values than this per list. */
export const MAX_REQUEST_VALUES = 20

const NAMES: Record<RequestFilterField, Record<RequestFilterMode, string>> = {
  user_agent: { include: 'user_agent', exclude: 'exclude_user_agent' },
  host: { include: 'host', exclude: 'exclude_host' },
  client_ip: { include: 'client_ip', exclude: 'exclude_client_ip' },
}

const ALL_NAMES = new Set(REQUEST_FILTER_FIELDS.flatMap(field => [NAMES[field].include, NAMES[field].exclude]))

export function requestFilterName(field: RequestFilterField, mode: RequestFilterMode): string {
  return NAMES[field][mode]
}

export function requestFilterValues(filters: AlertFilters, field: RequestFilterField, mode: RequestFilterMode): string[] {
  const value = filters[NAMES[field][mode]]
  return Array.isArray(value) ? value : []
}

function withValues(filters: AlertFilters, field: RequestFilterField, mode: RequestFilterMode, values: string[]): AlertFilters {
  const next = { ...filters }
  if (values.length) next[NAMES[field][mode]] = values
  else delete next[NAMES[field][mode]]
  return next
}

/**
 * Adds the value to the list of the mode, or takes it out when it is there. A value is shown or hidden, never
 * both, so adding it also takes it out of the other list. The twenty-first value is not added.
 */
export function toggleRequestValue(
  filters: AlertFilters,
  field: RequestFilterField,
  mode: RequestFilterMode,
  value: string,
): AlertFilters {
  const current = requestFilterValues(filters, field, mode)
  if (current.includes(value)) {
    return withValues(filters, field, mode, current.filter(v => v !== value))
  }
  if (current.length >= MAX_REQUEST_VALUES) return filters
  const other: RequestFilterMode = mode === 'include' ? 'exclude' : 'include'
  const kept = requestFilterValues(filters, field, other).filter(v => v !== value)
  return withValues(withValues(filters, field, other, kept), field, mode, [...current, value])
}

export function clearRequestFilters(filters: AlertFilters): AlertFilters {
  return Object.fromEntries(Object.entries(filters).filter(([name]) => !ALL_NAMES.has(name)))
}

export interface RequestFilterBadge {
  key: string
  field: RequestFilterField
  mode: RequestFilterMode
  value: string
  label: string
}

function shorten(text: string, length = 24): string {
  return text.length <= length ? text : `${text.slice(0, length)}…`
}

/** One badge per value, in the order of the fields. The key names field, mode and value, whatever characters it holds. */
export function requestFilterBadges(filters: AlertFilters): RequestFilterBadge[] {
  return REQUEST_FILTER_FIELDS.flatMap(field =>
    (['include', 'exclude'] as const).flatMap(mode =>
      requestFilterValues(filters, field, mode).map(value => ({
        key: JSON.stringify([field, mode, value]),
        field,
        mode,
        value,
        label: mode === 'exclude' ? `not ${shorten(value)}` : shorten(value),
      })),
    ),
  )
}

/** Only the request filters, as the lists the API takes. */
export function requestFilterQuery(filters: AlertFilters): Record<string, string[]> {
  return Object.fromEntries(
    Object.entries(filters).filter(([name, value]) => ALL_NAMES.has(name) && Array.isArray(value) && value.length),
  ) as Record<string, string[]>
}

/**
 * The filter object from the URL, which anyone can edit: text and numbers stay, a list stays when it holds
 * only non-empty text, and the rest is dropped.
 */
export function sanitizeFilters(parsed: Record<string, unknown>): AlertFilters {
  const clean: AlertFilters = {}
  for (const [name, value] of Object.entries(parsed)) {
    if (typeof value === 'string' || typeof value === 'number') clean[name] = value
    else if (Array.isArray(value) && value.length && value.length <= MAX_REQUEST_VALUES
      && value.every(item => typeof item === 'string' && item.length > 0)) {
      clean[name] = value as string[]
    }
  }
  return clean
}
