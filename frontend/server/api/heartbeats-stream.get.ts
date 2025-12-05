import { joinURL } from 'ufo'
import { proxyRequest } from 'h3'

const REFRESH_BUFFER_MS = 2 * 60 * 1000

/**
 * SSE Proxy for real-time heartbeat streaming.
 * Refreshes token inline if expired.
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

  return proxyRequest(event, target, {
    headers: {
      'Authorization': `Bearer ${session.secure!.apiToken}`,
      'Accept': 'text/event-stream',
      'Cache-Control': 'no-cache',
    },
  })
})
