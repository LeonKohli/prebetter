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
 * Always returns German locale as per system requirements
 */
function getUserLocale(): string {
  // Always use German locale as per system configuration
  return 'de-DE'
}

/**
 * Format a timestamp with consistent locale display (defaults to local timezone)
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

    const formatOptions: Intl.DateTimeFormatOptions = {
      dateStyle,
      timeStyle,
    }

    if (showTimezone) {
      formatOptions.timeZoneName = 'short'
    }

    return new Intl.DateTimeFormat(locale, formatOptions).format(date)
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
 * Format timestamp explicitly in the viewer's local timezone with abbreviation.
 */
export function formatTimestampLocal(
  timestamp: string | Date | number | undefined | null,
  options: Omit<TimestampOptions, 'showTimezone'> = {}
): string {
  return formatTimestamp(timestamp, {
    ...options,
    showTimezone: true,
  })
}
