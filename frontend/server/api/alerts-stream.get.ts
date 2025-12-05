import { joinURL } from 'ufo'
import { proxyRequest } from 'h3'

/**
 * SSE Proxy for real-time alert streaming.
 *
 * Uses h3's proxyRequest to stream SSE from backend to client.
 * Refreshes token if expired before proxying.
 */
export default defineEventHandler(async (event) => {
  const apiToken = await ensureValidToken(event)

  const apiBase = useRuntimeConfig().apiBase as string
  const target = joinURL(apiBase, 'api/v1/alerts/stream')

  return proxyRequest(event, target, {
    headers: {
      'Authorization': `Bearer ${apiToken}`,
      'Accept': 'text/event-stream',
      'Cache-Control': 'no-cache',
    },
  })
})
