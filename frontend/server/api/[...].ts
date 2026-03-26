import { joinURL } from 'ufo'
import type { H3Event } from 'h3'
import type { FetchError } from 'ofetch'
import { getSessionWithFreshTokens } from '#server/utils/auth-session'

// Auth endpoints must not be forwarded through the proxy — they expose JWT tokens.
const BLOCKED_PATHS = ['auth/token', 'auth/refresh']

/**
 * API Proxy - forwards requests to the backend API.
 * Refreshes access tokens before proxying since sessionHooks.fetch only fires on /api/_auth/session.
 */
export default defineEventHandler(async (event: H3Event) => {
  const path = event.path.replace(/^\/api\//, '')

  if (BLOCKED_PATHS.some((blocked) => path === blocked || path.startsWith(blocked + '/'))) {
    throw createError({ statusCode: 404, statusMessage: 'Not Found' })
  }

  const target = joinURL(useRuntimeConfig().apiBase as string, 'api/v1', path)

  const session = await getSessionWithFreshTokens(event)

  const headers: Record<string, string> = {
    accept: getRequestHeader(event, 'accept') || 'application/json',
  }
  if (session.secure?.apiToken) {
    headers['Authorization'] = `Bearer ${session.secure.apiToken}`
  }

  try {
    const fetchOptions: Record<string, unknown> = {
      method: event.method,
      headers,
      timeout: 30000,
    }
    if (event.method !== 'GET' && event.method !== 'HEAD') {
      const body = await readBody(event)
      if (body !== undefined) fetchOptions.body = body
    }
    return (await $fetch.raw(target, fetchOptions))._data
  } catch (error) {
    const fetchError = error as FetchError

    if (fetchError.statusCode === 401) {
      await clearUserSession(event)
    }

    if (fetchError.name === 'AbortError' || fetchError.message?.includes('timeout')) {
      throw createError({
        statusCode: 504,
        statusMessage: 'Gateway Timeout',
      })
    }

    if (fetchError.cause && String(fetchError.cause).includes('ECONNREFUSED')) {
      throw createError({
        statusCode: 503,
        statusMessage: 'Service Unavailable',
      })
    }

    // Pass backend errors through transparently — avoid Nuxt's createError
    // wrapping which nests data inside data (error.data.data.detail)
    setResponseStatus(event, fetchError.statusCode || 502, fetchError.statusMessage || 'Bad Gateway')
    return fetchError.data
  }
})
