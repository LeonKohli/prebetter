import { joinURL } from 'ufo'
import type { H3Event } from 'h3'
import type { FetchError } from 'ofetch'
import { auth } from '~~/server/utils/auth'

/**
 * API Proxy - forwards requests to the backend API.
 * Mints a short-lived Better Auth JWT for the current session and injects it as
 * a Bearer token, so the client never handles tokens. `/api/auth/*` is served by
 * Better Auth's own handler and never reaches this catch-all.
 */
export default defineEventHandler(async (event: H3Event) => {
  const path = event.path.replace(/^\/api\//, '')
  const target = joinURL(useRuntimeConfig().apiBase as string, 'api/v1', path)

  const headers: Record<string, string> = {
    accept: getRequestHeader(event, 'accept') || 'application/json',
  }

  try {
    const { token } = await auth.api.getToken({ headers: event.headers })
    if (token) headers['Authorization'] = `Bearer ${token}`
  } catch {
    // No valid session: forward unauthenticated and let the backend return 401.
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
