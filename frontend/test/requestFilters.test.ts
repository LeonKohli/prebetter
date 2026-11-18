import { describe, expect, it } from 'vitest'
import {
  MAX_REQUEST_VALUES,
  clearRequestFilters,
  requestFilterBadges,
  requestFilterQuery,
  requestFilterValues,
  sanitizeFilters,
  toggleRequestValue,
} from '../app/utils/requestFilters'

const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)'

describe('toggleRequestValue', () => {
  it('adds a value to the list of its mode and takes it out again', () => {
    const shown = toggleRequestValue({}, 'host', 'include', 'www.example.org')
    expect(shown).toEqual({ host: ['www.example.org'] })
    expect(toggleRequestValue(shown, 'host', 'include', 'www.example.org')).toEqual({})
  })

  it('keeps the other filters and leaves the given object alone', () => {
    const filters = { severity: 'high', host: ['a.example'] }
    const next = toggleRequestValue(filters, 'host', 'include', 'b.example')
    expect(next).toEqual({ severity: 'high', host: ['a.example', 'b.example'] })
    expect(filters).toEqual({ severity: 'high', host: ['a.example'] })
  })

  it('names the hidden values after the backend parameters', () => {
    expect(toggleRequestValue({}, 'user_agent', 'exclude', UA)).toEqual({ exclude_user_agent: [UA] })
  })

  it('shows or hides a value, never both', () => {
    const hidden = toggleRequestValue({}, 'client_ip', 'exclude', '203.0.113.9')
    const shown = toggleRequestValue(hidden, 'client_ip', 'include', '203.0.113.9')
    expect(shown).toEqual({ client_ip: ['203.0.113.9'] })
    expect(toggleRequestValue(shown, 'client_ip', 'exclude', '203.0.113.9')).toEqual({ exclude_client_ip: ['203.0.113.9'] })
  })

  it('does not add past the limit of the backend', () => {
    const full = { host: Array.from({ length: MAX_REQUEST_VALUES }, (_, n) => `h${n}.example`) }
    expect(toggleRequestValue(full, 'host', 'include', 'one-more.example')).toBe(full)
    expect(toggleRequestValue(full, 'host', 'include', 'h0.example').host).toHaveLength(MAX_REQUEST_VALUES - 1)
  })
})

describe('requestFilterValues', () => {
  it('reads a list and treats anything else as empty', () => {
    expect(requestFilterValues({ host: ['a'] }, 'host', 'include')).toEqual(['a'])
    expect(requestFilterValues({ host: 'a' }, 'host', 'include')).toEqual([])
    expect(requestFilterValues({}, 'host', 'exclude')).toEqual([])
  })
})

describe('requestFilterBadges', () => {
  it('lists each value once, shown before hidden, in the order of the fields', () => {
    const badges = requestFilterBadges({ exclude_user_agent: ['scanner/1.0'], host: ['a.example'], user_agent: ['curl/8'] })
    expect(badges.map(b => b.label)).toEqual(['curl/8', 'not scanner/1.0', 'a.example'])
  })

  it('shortens a long value and keys it so that colons and commas stay intact', () => {
    const [badge] = requestFilterBadges({ user_agent: [UA] })
    expect(badge!.label).toBe(`${UA.slice(0, 24)}…`)
    expect(JSON.parse(badge!.key)).toEqual(['user_agent', 'include', UA])
  })

  it('is empty without request filters', () => {
    expect(requestFilterBadges({ severity: 'high' })).toEqual([])
  })
})

describe('requestFilterQuery and clearRequestFilters', () => {
  const filters = { severity: 'high', host: ['a.example'], exclude_client_ip: ['10.0.0.0/8'], user_agent: [] as string[] }

  it('takes only the request filters, with a list each', () => {
    expect(requestFilterQuery(filters)).toEqual({ host: ['a.example'], exclude_client_ip: ['10.0.0.0/8'] })
  })

  it('removes the request filters and nothing else', () => {
    expect(clearRequestFilters(filters)).toEqual({ severity: 'high' })
  })
})

describe('sanitizeFilters', () => {
  it('keeps text, numbers and lists of text', () => {
    expect(sanitizeFilters({ severity: 'high', page: 2, host: ['a.example'] })).toEqual({ severity: 'high', page: 2, host: ['a.example'] })
  })

  it.each([
    ['objects', { host: { a: 1 } }],
    ['mixed lists', { host: ['a', 1] }],
    ['lists with empty text', { host: [''] }],
    ['empty lists', { host: [] }],
    ['booleans', { x: true }],
    ['null', { x: null }],
  ])('drops %s', (_name, parsed) => {
    expect(sanitizeFilters(parsed)).toEqual({})
  })

  it('drops a list longer than the backend takes', () => {
    expect(sanitizeFilters({ host: Array.from({ length: MAX_REQUEST_VALUES + 1 }, (_, n) => `h${n}`) })).toEqual({})
  })
})
