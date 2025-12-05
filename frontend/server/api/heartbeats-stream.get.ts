import { joinURL } from 'ufo'
import { proxyRequest } from 'h3'

/**
 * SSE Proxy for real-time heartbeat streaming.
 *
 * Uses h3's proxyRequest to stream SSE from backend to client.
 */
export default defineEventHandler(async (event) => {
  const session = await getUserSession(event)

  if (!session.secure?.apiToken) {
    throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
  }

  const apiBase = useRuntimeConfig().apiBase as string
  const target = joinURL(apiBase, 'api/v1/heartbeats/stream')

  return proxyRequest(event, target, {
    headers: {
      'Authorization': `Bearer ${session.secure.apiToken}`,
      'Accept': 'text/event-stream',
      'Cache-Control': 'no-cache',
    },
  })
})
