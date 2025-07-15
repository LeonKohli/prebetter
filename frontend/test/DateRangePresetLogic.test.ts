import { describe, it, expect } from 'vitest'

// Extract and test the core preset detection logic directly
describe('Date Range Preset Detection Logic', () => {
  // This is the core logic we extracted from the component for testing
  function findBestPresetMatch(
    userFrom: number,
    userTo: number,
    presets: Array<{ label: string; from: number; to: number }>
  ) {
    let bestMatch = null
    let bestScore = Infinity
    
    for (const preset of presets) {
      const fromDiff = Math.abs(userFrom - preset.from)
      const toDiff = Math.abs(userTo - preset.to)
      const totalDiff = fromDiff + toDiff
      
      // Realistic tolerance based on preset type and real-world variations
      const label = preset.label.toLowerCase()
      const timeSpan = Math.abs(preset.to - preset.from)
      let tolerance: number
      
      if (label.includes('hour')) {
        // Hour presets: reasonable tolerance for user interaction delays
        tolerance = 15 * 60 * 1000 // 15 minutes
      } else if (label === 'today') {
        // Today preset: handle as single day - very flexible since it's often 00:00-23:59
        tolerance = 12 * 60 * 60 * 1000 // 12 hours
      } else if (label.includes('week') || label.includes('this week') || label.includes('last 7') || label.includes('7 days')) {
        // Week presets: week boundaries can vary significantly (check before 'day' to avoid conflict)
        tolerance = 2 * 24 * 60 * 60 * 1000 // 2 days
      } else if (label.includes('month') || label.includes('this month') || label.includes('30 days')) {
        // Month presets: month boundaries vary
        tolerance = 3 * 24 * 60 * 60 * 1000 // 3 days
      } else if (label.includes('year') || label.includes('this year')) {
        // Year presets: year boundaries
        tolerance = 7 * 24 * 60 * 60 * 1000 // 1 week
      } else if (label.includes('day')) {
        // Day presets: account for timezone and daylight savings variations (check after week/month)
        tolerance = 4 * 60 * 60 * 1000 // 4 hours
      } else {
        // Default: use 5% of the time span as tolerance, minimum 1 hour
        tolerance = Math.max(60 * 60 * 1000, timeSpan * 0.05)
      }
      
      const fromMatch = fromDiff <= tolerance
      const toMatch = toDiff <= tolerance
      
      // If both match and this is the best score so far
      if (fromMatch && toMatch && totalDiff < bestScore) {
        bestScore = totalDiff
        bestMatch = preset
      }
    }
    
    return bestMatch
  }

  describe('Hour-based preset detection', () => {
    it('should detect "Last 1 Hour" preset correctly', () => {
      const now = new Date('2024-01-15T10:30:00Z').getTime()
      const oneHourAgo = now - 60 * 60 * 1000
      
      const presets = [
        { label: 'Today', from: new Date('2024-01-15T00:00:00Z').getTime(), to: new Date('2024-01-15T23:59:59Z').getTime() },
        { label: 'Last 1 Hour', from: oneHourAgo, to: now },
        { label: 'Last 2 Hours', from: now - 2 * 60 * 60 * 1000, to: now }
      ]
      
      const result = findBestPresetMatch(oneHourAgo, now, presets)
      expect(result?.label).toBe('Last 1 Hour')
    })

    it('should detect "Last 2 Hours" preset correctly', () => {
      const now = new Date('2024-01-15T10:30:00Z').getTime()
      const twoHoursAgo = now - 2 * 60 * 60 * 1000
      
      const presets = [
        { label: 'Today', from: new Date('2024-01-15T00:00:00Z').getTime(), to: new Date('2024-01-15T23:59:59Z').getTime() },
        { label: 'Last 1 Hour', from: now - 60 * 60 * 1000, to: now },
        { label: 'Last 2 Hours', from: twoHoursAgo, to: now }
      ]
      
      const result = findBestPresetMatch(twoHoursAgo, now, presets)
      expect(result?.label).toBe('Last 2 Hours')
    })

    it('should NOT detect hour presets as "Today"', () => {
      const now = new Date('2024-01-15T10:30:00Z').getTime()
      const oneHourAgo = now - 60 * 60 * 1000
      
      const presets = [
        { label: 'Today', from: new Date('2024-01-15T00:00:00Z').getTime(), to: new Date('2024-01-15T23:59:59Z').getTime() },
        { label: 'Last 1 Hour', from: oneHourAgo, to: now }
      ]
      
      const result = findBestPresetMatch(oneHourAgo, now, presets)
      expect(result?.label).not.toBe('Today')
      expect(result?.label).toBe('Last 1 Hour')
    })
  })

  describe('Today preset detection', () => {
    it('should detect "Today" preset for exact day boundaries', () => {
      const startOfDay = new Date('2024-01-15T00:00:00Z').getTime()
      const endOfDay = new Date('2024-01-15T23:59:59.999Z').getTime()
      
      const presets = [
        { label: 'Today', from: startOfDay, to: endOfDay },
        { label: 'Last 1 Hour', from: endOfDay - 60 * 60 * 1000, to: endOfDay }
      ]
      
      const result = findBestPresetMatch(startOfDay, endOfDay, presets)
      expect(result?.label).toBe('Today')
    })

    it('should detect "Today" for full day ranges', () => {
      const startOfDay = new Date('2024-01-15T00:00:00Z').getTime()
      const endOfDay = new Date('2024-01-15T23:59:59Z').getTime()
      
      const presets = [
        { label: 'Today', from: startOfDay, to: endOfDay }
      ]
      
      const result = findBestPresetMatch(startOfDay, endOfDay, presets)
      expect(result?.label).toBe('Today')
    })
  })

  describe('Week preset detection', () => {
    it('should detect "Last 7 Days" with generous tolerance', () => {
      const now = new Date('2024-01-15T10:30:00Z').getTime()
      const weekAgo = now - 7 * 24 * 60 * 60 * 1000
      // Off by 1 day (should match with 2-day tolerance)
      const almostWeekAgo = weekAgo - 24 * 60 * 60 * 1000
      
      const presets = [
        { label: 'Last 7 Days', from: weekAgo, to: now }
      ]
      
      const result = findBestPresetMatch(almostWeekAgo, now, presets)
      expect(result?.label).toBe('Last 7 Days')
    })

    it('should detect "This Week" with generous tolerance', () => {
      const now = new Date('2024-01-15T10:30:00Z').getTime()
      const weekStart = new Date('2024-01-14T00:00:00Z').getTime()
      const weekEnd = new Date('2024-01-20T23:59:59Z').getTime()
      
      const presets = [
        { label: 'This Week', from: weekStart, to: weekEnd }
      ]
      
      const result = findBestPresetMatch(weekStart, weekEnd, presets)
      expect(result?.label).toBe('This Week')
    })
  })

  describe('Tolerance levels', () => {
    it('should use reasonable tolerance for hour presets', () => {
      const now = new Date('2024-01-15T10:30:00Z').getTime()
      // Slightly off by 10 minutes (should still match with 15-minute tolerance)
      const almostOneHourAgo = now - 60 * 60 * 1000 - 10 * 60 * 1000
      
      const presets = [
        { label: 'Last 1 Hour', from: now - 60 * 60 * 1000, to: now }
      ]
      
      const result = findBestPresetMatch(almostOneHourAgo, now, presets)
      expect(result?.label).toBe('Last 1 Hour')
    })

    it('should NOT match hour presets with very large tolerance differences', () => {
      const now = new Date('2024-01-15T10:30:00Z').getTime()
      // Off by 30 minutes (should NOT match with 15-minute tolerance)
      const wayOffOneHour = now - 60 * 60 * 1000 - 30 * 60 * 1000
      
      const presets = [
        { label: 'Last 1 Hour', from: now - 60 * 60 * 1000, to: now }
      ]
      
      const result = findBestPresetMatch(wayOffOneHour, now, presets)
      expect(result).toBeNull()
    })

    it('should be very forgiving for Today preset', () => {
      const startOfDay = new Date('2024-01-15T00:00:00Z').getTime()
      // Off by several hours (should match with 12-hour tolerance)
      const almostEndOfDay = new Date('2024-01-15T20:00:00Z').getTime()
      
      const presets = [
        { label: 'Today', from: startOfDay, to: new Date('2024-01-15T23:59:59Z').getTime() }
      ]
      
      const result = findBestPresetMatch(startOfDay, almostEndOfDay, presets)
      expect(result?.label).toBe('Today')
    })
  })

  describe('Priority and best match selection', () => {
    it('should select the most accurate match when multiple presets could match', () => {
      const now = new Date('2024-01-15T10:30:00Z').getTime()
      const oneHourAgo = now - 60 * 60 * 1000
      
      const presets = [
        { label: 'Today', from: new Date('2024-01-15T00:00:00Z').getTime(), to: new Date('2024-01-15T23:59:59Z').getTime() },
        { label: 'Last 1 Hour', from: oneHourAgo, to: now },
        { label: 'Last 2 Hours', from: now - 2 * 60 * 60 * 1000, to: now }
      ]
      
      // Should match "Last 1 Hour" specifically, not any broader preset
      const result = findBestPresetMatch(oneHourAgo, now, presets)
      expect(result?.label).toBe('Last 1 Hour')
    })
  })

  describe('Edge cases', () => {
    it('should return null for completely unmatched ranges', () => {
      const start = new Date('2024-01-15T10:30:00Z').getTime()
      const end = start + 45 * 60 * 1000 // 45 minutes - should not match hour presets
      
      const presets = [
        { label: 'Last 1 Hour', from: start - 60 * 60 * 1000, to: start },
        { label: 'Last 2 Hours', from: start - 2 * 60 * 60 * 1000, to: start }
      ]
      
      const result = findBestPresetMatch(start, end, presets)
      expect(result).toBeNull()
    })
  })

  describe('Bug reproduction: Fixed tolerance logic', () => {
    it('should properly categorize Last 7 Days as a week preset', () => {
      const now = new Date('2024-01-15T10:30:00Z').getTime()
      const oneWeekAgo = now - 7 * 24 * 60 * 60 * 1000
      
      const presets = [
        { label: 'Last 7 Days', from: oneWeekAgo, to: now },
        { label: 'Last 2 Days', from: now - 2 * 24 * 60 * 60 * 1000, to: now }
      ]
      
      // Should match "Last 7 Days" with week tolerance (2 days), not day tolerance (4 hours)
      const result = findBestPresetMatch(oneWeekAgo, now, presets)
      expect(result?.label).toBe('Last 7 Days')
    })

    it('demonstrates that a 15-minute range should not match any preset', () => {
      const now = new Date('2024-01-15T10:30:00Z').getTime()
      const fifteenMinutesAgo = now - 15 * 60 * 1000 // 15 minutes ago
      
      const presets = [
        { label: 'Today', from: new Date('2024-01-15T00:00:00Z').getTime(), to: new Date('2024-01-15T23:59:59Z').getTime() },
        { label: 'Last 1 Hour', from: now - 60 * 60 * 1000, to: now }
      ]
      
      // 15 minutes is too specific to match broader presets like Today or Last 1 Hour
      const result = findBestPresetMatch(fifteenMinutesAgo, now, presets)
      expect(result).toBeNull()
    })
  })
})