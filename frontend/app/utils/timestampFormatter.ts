/**
 * Centralized timestamp formatting utility for consistent time display
 * across the application with proper timezone handling
 */

export interface TimestampOptions {
  /** Display timezone indicator (default: true) */
  showTimezone?: boolean
  /** Use relative time for recent timestamps (default: false) */
  useRelative?: boolean
  /** Custom locale (default: browser locale or 'en-US') */
  locale?: string
  /** Display format style */
  style?: 'full' | 'long' | 'medium' | 'short'
}

/**
 * Get the user's locale in an SSR-safe way
 */
function getUserLocale(): string {
  // Check if we're on the client side and navigator is available
  if (process.client && typeof navigator !== 'undefined' && navigator.language) {
    return navigator.language
  }
  // Default to en-US for server-side rendering
  return 'en-US'
}

/**
 * Format a timestamp with consistent locale and timezone display
 * @param timestamp - ISO string, Date object, or unix timestamp
 * @param options - Formatting options
 * @returns Formatted timestamp string
 */
export function formatTimestamp(
  timestamp: string | Date | number | undefined | null,
  options: TimestampOptions = {}
): string {
  if (!timestamp) return 'N/A'

  const {
    showTimezone = true,
    useRelative = false,
    locale = getUserLocale(),
    style = 'medium'
  } = options

  try {
    const date = timestamp instanceof Date
      ? timestamp
      : new Date(timestamp)

    // Check if date is valid
    if (isNaN(date.getTime())) {
      return 'Invalid date'
    }

    // Use relative time for recent timestamps if requested
    if (useRelative) {
      const now = new Date()
      const diffMs = now.getTime() - date.getTime()
      const diffMins = Math.floor(diffMs / 60000)

      if (diffMins < 1) return 'Just now'
      if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`

      const diffHours = Math.floor(diffMins / 60)
      if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`

      const diffDays = Math.floor(diffHours / 24)
      if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
    }

    // Format with locale and timezone
    const dateStyle = style === 'full' || style === 'long' ? style : 'medium'
    const timeStyle = style === 'short' ? 'short' : 'medium'

    const formatted = new Intl.DateTimeFormat(locale, {
      dateStyle,
      timeStyle,
      timeZone: 'UTC', // Always display in UTC for consistency
    }).format(date)

    // Add timezone indicator if requested
    if (showTimezone) {
      return `${formatted} UTC`
    }

    return formatted
  } catch (error) {
    console.error('Error formatting timestamp:', error)
    return 'Invalid date'
  }
}

/**
 * Format timestamp for display in tables (compact format)
 */
export function formatTimestampCompact(timestamp: string | Date | number | undefined | null): string {
  return formatTimestamp(timestamp, {
    style: 'short',
    showTimezone: false // Omit timezone in tables for space
  })
}

/**
 * Format timestamp for detailed views (full format with timezone)
 */
export function formatTimestampDetailed(timestamp: string | Date | number | undefined | null): string {
  return formatTimestamp(timestamp, {
    style: 'long',
    showTimezone: true
  })
}

/**
 * Get a human-readable relative time string
 */
export function getRelativeTime(timestamp: string | Date | number | undefined | null): string {
  return formatTimestamp(timestamp, {
    useRelative: true,
    showTimezone: false
  })
}

/**
 * Convert UTC timestamp to local time for display
 * Use this when you need to show local time instead of UTC
 */
export function formatTimestampLocal(
  timestamp: string | Date | number | undefined | null,
  options: Omit<TimestampOptions, 'showTimezone'> = {}
): string {
  if (!timestamp) return 'N/A'

  const {
    locale = getUserLocale(),
    style = 'medium'
  } = options

  try {
    const date = timestamp instanceof Date
      ? timestamp
      : new Date(timestamp)

    if (isNaN(date.getTime())) {
      return 'Invalid date'
    }

    const dateStyle = style === 'full' || style === 'long' ? style : 'medium'
    const timeStyle = style === 'short' ? 'short' : 'medium'

    // Format in local timezone
    const formatted = new Intl.DateTimeFormat(locale, {
      dateStyle,
      timeStyle,
      // No timeZone specified = use browser's local timezone
    }).format(date)

    // Get timezone abbreviation
    const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone
    const tzAbbr = new Date().toLocaleTimeString('en-US', {
      timeZoneName: 'short',
      timeZone
    }).split(' ').pop()

    return `${formatted} ${tzAbbr}`
  } catch (error) {
    console.error('Error formatting local timestamp:', error)
    return 'Invalid date'
  }
}