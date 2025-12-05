import { joinURL } from 'ufo'

const REFRESH_BUFFER_MS = 2 * 60 * 1000

/**
 * SSE Proxy for real-time alert streaming.
 *
 * Uses manual fetch + streaming instead of proxyRequest which has
 * known issues with SSE connections in Nuxt/h3.
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

  const target = joinURL(config.apiBase as string, 'api/v1/alerts/stream')

  // Fetch SSE from backend
  const response = await fetch(target, {
    headers: {
      'Authorization': `Bearer ${session.secure!.apiToken}`,
      'Accept': 'text/event-stream',
      'Cache-Control': 'no-cache',
    },
  })

  if (!response.ok || !response.body) {
    throw createError({
      statusCode: response.status,
      statusMessage: response.statusText || 'Failed to connect to SSE stream',
    })
  }

  // Set SSE headers - critical for proper streaming
  setResponseHeader(event, 'Content-Type', 'text/event-stream')
  setResponseHeader(event, 'Cache-Control', 'no-cache, no-transform')
  setResponseHeader(event, 'Connection', 'keep-alive')
  setResponseHeader(event, 'X-Accel-Buffering', 'no')

  // Stream the response body directly
  return sendStream(event, response.body)
})
