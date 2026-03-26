import { joinURL } from 'ufo'
import type { H3Event } from 'h3'
import type { FetchError } from 'ofetch'

const REFRESH_BUFFER_MS = 2 * 60 * 1000 // Refresh 2 min before expiry

type RefreshedTokens = {
  apiToken: string
  refreshToken: string
  expiresAt: number
}

// Deduplicate only identical refresh attempts. Different user sessions must never
// share refreshed tokens, even within the same server process.
const inFlightRefreshes = new Map<string, Promise<RefreshedTokens>>()

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
      const currentRefreshToken = session.secure.refreshToken

      let refreshPromise = inFlightRefreshes.get(currentRefreshToken)
      if (!refreshPromise) {
        refreshPromise = (async (): Promise<RefreshedTokens> => {
          const tokens = await $fetch<{
            access_token: string
            refresh_token: string
            expires_in: number
          }>(`${useRuntimeConfig().apiBase}/api/v1/auth/refresh`, {
            method: 'POST',
            body: { refresh_token: currentRefreshToken },
          })

          return {
            apiToken: tokens.access_token,
            refreshToken: tokens.refresh_token,
            expiresAt: Date.now() + tokens.expires_in * 1000,
          }
        })()

        inFlightRefreshes.set(currentRefreshToken, refreshPromise)
      }

      try {
        const refreshed = await refreshPromise

        await setUserSession(event, {
          ...session,
          secure: {
            apiToken: refreshed.apiToken,
            refreshToken: refreshed.refreshToken,
          },
          tokenExpiresAt: refreshed.expiresAt,
        })

        session = {
          ...session,
          secure: {
            apiToken: refreshed.apiToken,
            refreshToken: refreshed.refreshToken,
          },
          tokenExpiresAt: refreshed.expiresAt,
        }
      } catch {
        await clearUserSession(event)
        throw createError({ statusCode: 401, statusMessage: 'Session expired' })
      } finally {
        if (inFlightRefreshes.get(currentRefreshToken) === refreshPromise) {
          inFlightRefreshes.delete(currentRefreshToken)
        }
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

    // Pass backend errors through transparently — avoid Nuxt's createError
    // wrapping which nests data inside data (error.data.data.detail)
    setResponseStatus(event, fetchError.statusCode || 502, fetchError.statusMessage || 'Bad Gateway')
    return fetchError.data
  }
})
