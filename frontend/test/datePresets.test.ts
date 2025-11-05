import { beforeAll, describe, expect, it } from 'vitest'

let datePresets: typeof import('@/utils/datePresets')

const iso = (date: Date) => date.toISOString()

beforeAll(async () => {
  process.env.TZ = 'UTC'
  datePresets = await import('@/utils/datePresets')
})

describe('datePresets', () => {
  it('normalizes "Today" to start/end of day boundaries', () => {
    const now = new Date('2025-03-12T10:42:33.000Z')
    const range = datePresets.getPresetRange('today', now)
    expect(iso(range.from)).toBe('2025-03-12T00:00:00.000Z')
    expect(iso(range.to)).toBe('2025-03-12T23:59:59.999Z')
  })

  it('produces inclusive full-day window for relative day presets', () => {
    const now = new Date('2024-03-15T15:30:00.000Z')
    const range = datePresets.getPresetRange('last-7-days', now)
    expect(iso(range.from)).toBe('2024-03-08T00:00:00.000Z')
    expect(iso(range.to)).toBe('2024-03-15T23:59:59.999Z')
    expect(datePresets.isRelativePreset('last-7-days')).toBe(true)
  })

  it('handles month presets without overflowing for end-of-month dates', () => {
    const now = new Date('2024-03-31T11:15:00.000Z')
    const range = datePresets.getPresetRange('last-3-months', now)
    expect(iso(range.from)).toBe('2023-12-31T00:00:00.000Z')
    expect(iso(range.to)).toBe('2024-03-31T23:59:59.999Z')
  })

  it('keeps leap year boundaries stable for last-year preset', () => {
    const now = new Date('2024-02-29T09:00:00.000Z')
    const range = datePresets.getPresetRange('last-year', now)
    expect(iso(range.from)).toBe('2023-02-28T00:00:00.000Z')
    expect(iso(range.to)).toBe('2024-02-29T23:59:59.999Z')
  })

  it('uses locale-aware Monday start for "This Week"', () => {
    const now = new Date('2024-05-05T12:00:00.000Z') // Sunday, expect Monday start
    const range = datePresets.getPresetRange('this-week', now)
    expect(iso(range.from)).toBe('2024-04-29T00:00:00.000Z')
    expect(iso(range.to)).toBe('2024-05-05T23:59:59.999Z')
    expect(datePresets.isRelativePreset('this-week')).toBe(false)
  })
})
