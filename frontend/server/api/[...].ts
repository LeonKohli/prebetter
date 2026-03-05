import { joinURL } from 'ufo'
import type { H3Event } from 'h3'
import type { FetchError } from 'ofetch'

const REFRESH_BUFFER_MS = 2 * 60 * 1000 // Refresh 2 min before expiry

// Module-level lock: ensures only one token refresh runs at a time.
// Concurrent requests that also need a refresh will await the same promise.
let refreshPromise: Promise<void> | null = null

// Auth endpoints must not be forwarded through the proxy — they expose JWT tokens.
const BLOCKED_PATHS = ['auth/token', 'auth/refresh']

/**
 * API Proxy - forwards requests to the backend API.
 * Handles token refresh inline since sessionHooks.fetch only fires on /api/_auth/session.
 */
export default defineEventHandler(async (event: H3Event) => {
  const path = event.path.replace(/^\/api\//, '')

  if (BLOCKED_PATHS.some((blocked) => path === blocked || path.startsWith(blocked + '/'))) {
    throw createError({ statusCode: 404, statusMessage: 'Not Found' })
  }

  const target = joinURL(useRuntimeConfig().apiBase as string, 'api/v1', path)

  let session = await getUserSession(event)

  if (session.user && session.secure?.apiToken && session.secure?.refreshToken && session.tokenExpiresAt) {
    const needsRefresh = Date.now() + REFRESH_BUFFER_MS >= session.tokenExpiresAt

    if (needsRefresh) {
      if (refreshPromise) {
        await refreshPromise
        session = await getUserSession(event)
      } else {
        refreshPromise = (async () => {
          try {
            const tokens = await $fetch<{
              access_token: string
              refresh_token: string
              expires_in: number
            }>(`${useRuntimeConfig().apiBase}/api/v1/auth/refresh`, {
              method: 'POST',
              body: { refresh_token: session.secure!.refreshToken },
            })

            await setUserSession(event, {
              ...session,
              secure: {
                apiToken: tokens.access_token,
                refreshToken: tokens.refresh_token,
              },
              tokenExpiresAt: Date.now() + tokens.expires_in * 1000,
            })
          } catch {
            await clearUserSession(event)
            throw createError({ statusCode: 401, statusMessage: 'Session expired' })
          } finally {
            refreshPromise = null
          }
        })()

        await refreshPromise
        session = await getUserSession(event)
      }
    }
  }

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

    throw createError({
      statusCode: fetchError.statusCode || 502,
      statusMessage: fetchError.statusMessage || 'Bad Gateway',
      data: fetchError.data,
    })
  }
})
