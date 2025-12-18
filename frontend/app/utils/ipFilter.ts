export interface IPFilterResult {
  isValid: boolean
  isRange: boolean
  original: string
  expanded: string | null
  error: string | null
}

function isValidOctet(s: string): boolean {
  if (!s || !/^\d+$/.test(s)) return false
  const val = parseInt(s, 10)
  return val >= 0 && val <= 255
}

function expandPartialIP(segments: string[]): { min: string; max: string } {
  const minSegments = [...segments, ...Array(4 - segments.length).fill('0')]
  const maxSegments = [...segments, ...Array(4 - segments.length).fill('255')]
  return {
    min: minSegments.join('.'),
    max: maxSegments.join('.'),
  }
}

function parseCIDR(value: string): { network: string; broadcast: string } | null {
  const [ip, prefixStr] = value.split('/')
  if (!ip || !prefixStr) return null
  const prefix = parseInt(prefixStr, 10)
  if (isNaN(prefix) || prefix < 0 || prefix > 32) return null

  const segments = ip.split('.')
  if (segments.length !== 4 || !segments.every(isValidOctet)) return null

  const ipNum = segments.reduce((acc, seg) => (acc << 8) + parseInt(seg, 10), 0) >>> 0
  const mask = prefix === 0 ? 0 : (~0 << (32 - prefix)) >>> 0
  const network = ipNum & mask
  const broadcast = network | (~mask >>> 0)

  const toIP = (num: number) =>
    [(num >>> 24) & 0xff, (num >>> 16) & 0xff, (num >>> 8) & 0xff, num & 0xff].join('.')

  return { network: toIP(network), broadcast: toIP(broadcast) }
}

export function parseIPFilter(value: string): IPFilterResult {
  const trimmed = value.trim()

  if (!trimmed) {
    return { isValid: false, isRange: false, original: '', expanded: null, error: null }
  }

  if (trimmed.includes('/')) {
    const result = parseCIDR(trimmed)
    if (!result) {
      return { isValid: false, isRange: false, original: trimmed, expanded: null, error: 'Invalid CIDR notation' }
    }
    return {
      isValid: true,
      isRange: true,
      original: trimmed,
      expanded: `${result.network} - ${result.broadcast}`,
      error: null,
    }
  }

  const segments = trimmed.split('.')

  if (segments.length < 4 && segments.length >= 1 && segments.every(isValidOctet)) {
    const { min, max } = expandPartialIP(segments)
    return {
      isValid: true,
      isRange: true,
      original: trimmed,
      expanded: `${min} - ${max}`,
      error: null,
    }
  }

  if (segments.length === 4 && segments.every(isValidOctet)) {
    return {
      isValid: true,
      isRange: false,
      original: trimmed,
      expanded: trimmed,
      error: null,
    }
  }

  return { isValid: false, isRange: false, original: trimmed, expanded: null, error: 'Invalid IP address' }
}

export function getIPFilterHint(value: string): string | null {
  if (!value.trim()) return null
  const result = parseIPFilter(value)
  if (!result.isValid) return result.error
  if (result.isRange && result.expanded !== result.original) {
    return `Matches: ${result.expanded}`
  }
  return null
}
