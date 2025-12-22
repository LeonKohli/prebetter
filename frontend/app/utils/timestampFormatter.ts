/**
 * Centralized timestamp formatting utility for consistent time display
 * across the application with proper timezone handling
 *
 * Note: For relative time ("5 minutes ago"), use the TimeAgo component
 * which uses VueUse's useTimeAgo for reactive updates.
 */

interface TimestampOptions {
  /** Display timezone indicator (default: true) */
  showTimezone?: boolean
  /** Custom locale (default: 'de-DE') */
  locale?: string
  /** Display format style */
  style?: 'full' | 'long' | 'medium' | 'short'
}

/**
 * Get the user's locale in an SSR-safe way
 * Always returns German locale as per system requirements
 */
function getUserLocale(): string {
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

    // Note: Cannot use dateStyle/timeStyle with timeZoneName
    // Must use component options instead
    const formatOptions: Intl.DateTimeFormatOptions = showTimezone ? {
      year: 'numeric',
      month: style === 'short' ? 'numeric' : '2-digit',
      day: style === 'short' ? 'numeric' : '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: style === 'short' ? undefined : '2-digit',
      timeZoneName: 'short'
    } : {
      dateStyle: style === 'full' || style === 'long' ? style : 'medium',
      timeStyle: style === 'short' ? 'short' : 'medium',
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
    showTimezone: false
  })
}
