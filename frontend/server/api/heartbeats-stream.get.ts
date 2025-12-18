import { joinURL } from 'ufo'

const REFRESH_BUFFER_MS = 2 * 60 * 1000

/**
 * SSE Proxy for real-time heartbeat streaming.
 *
 * CRITICAL: Uses AbortController to cancel backend fetch when client disconnects.
 * Without this, backend SSE connections accumulate and never close.
 */
export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  let session = await getUserSession(event)

  if (!session.secure?.apiToken) {
    throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
  }

  // Refresh token if needed
  if (session.tokenExpiresAt && Date.now() + REFRESH_BUFFER_MS >= session.tokenExpiresAt) {
    try {
      const tokens = await $fetch<{ access_token: string; refresh_token: string; expires_in: number }>(
        `${config.apiBase}/api/v1/auth/refresh`,
        { method: 'POST', body: { refresh_token: session.secure.refreshToken } }
      )
      await setUserSession(event, {
        ...session,
        secure: { apiToken: tokens.access_token, refreshToken: tokens.refresh_token },
        tokenExpiresAt: Date.now() + tokens.expires_in * 1000,
      })
      session = await getUserSession(event)
    } catch {
      await clearUserSession(event)
      throw createError({ statusCode: 401, statusMessage: 'Session expired' })
    }
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
