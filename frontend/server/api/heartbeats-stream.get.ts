import { joinURL } from 'ufo'
import { getSessionWithFreshTokens } from '#server/utils/auth-session'

/**
 * SSE Proxy for real-time heartbeat streaming.
 *
 * CRITICAL: Uses AbortController to cancel backend fetch when client disconnects.
 * Without this, backend SSE connections accumulate and never close.
 */
export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const session = await getSessionWithFreshTokens(event)

  if (!session.secure?.apiToken) {
    throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
  }

  const target = joinURL(config.apiBase as string, 'api/v1/heartbeats/stream')

  // AbortController to cancel backend fetch when client disconnects
  const abortController = new AbortController()

  const timeoutId = setTimeout(() => abortController.abort(), 10000)

  let response: Response
  try {
    response = await fetch(target, {
      headers: {
        'Authorization': `Bearer ${session.secure!.apiToken}`,
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache',
      },
      signal: abortController.signal,
    })
  } catch (err) {
    clearTimeout(timeoutId)
    if ((err as Error).name === 'AbortError') {
      throw createError({ statusCode: 504, statusMessage: 'Backend connection timeout' })
    }
    throw createError({ statusCode: 503, statusMessage: 'Backend unavailable' })
  }
  clearTimeout(timeoutId)

  if (!response.ok || !response.body) {
    throw createError({
      statusCode: response.status,
      statusMessage: response.statusText || 'Failed to connect to SSE stream',
    })
  }

  // Set SSE headers
  setResponseHeader(event, 'Content-Type', 'text/event-stream')
  setResponseHeader(event, 'Cache-Control', 'no-cache, no-transform')
  setResponseHeader(event, 'Connection', 'keep-alive')
  setResponseHeader(event, 'X-Accel-Buffering', 'no')

  // Listen for client disconnect and abort backend fetch
  event.node.req.on('close', () => {
    abortController.abort()
  })

  // Stream the response body directly
  return sendStream(event, response.body)
})
