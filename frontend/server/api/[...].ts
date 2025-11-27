import { joinURL } from 'ufo'
import type { H3Event } from 'h3'
import type { FetchError } from 'ofetch'

/**
 * API Proxy - forwards requests to the backend API.
 * Token refresh handled by session fetch hook in server/plugins/session.ts.
 */
export default defineEventHandler(async (event: H3Event) => {
  const path = event.path.replace(/^\/api\//, '')
  const target = joinURL(useRuntimeConfig().apiBase as string, 'api/v1', path)

  const session = await getUserSession(event)
  const headers: Record<string, string> = {
    accept: getRequestHeader(event, 'accept') || 'application/json',
  }
  if (session.secure?.apiToken) {
    headers['Authorization'] = `Bearer ${session.secure.apiToken}`
  }

  try {
    const fetchOptions: Record<string, unknown> = { method: event.method, headers }
    if (event.method !== 'GET' && event.method !== 'HEAD') {
      const body = await readBody(event)
      if (body !== undefined) fetchOptions.body = body
    }
    return (await $fetch.raw(target, fetchOptions))._data
  } catch (error) {
    const fetchError = error as FetchError

    // 401 = clear session, client middleware handles redirect on next navigation
    if (fetchError.statusCode === 401) {
      await clearUserSession(event)
    }

    throw createError({
      statusCode: fetchError.statusCode || 502,
      statusMessage: fetchError.statusMessage || 'Bad Gateway',
      data: fetchError.data,
    })
  }
})
