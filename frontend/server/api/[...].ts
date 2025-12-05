import { joinURL } from 'ufo'
import type { H3Event } from 'h3'
import type { FetchError } from 'ofetch'

const REFRESH_BUFFER_MS = 2 * 60 * 1000 // Refresh 2 min before expiry

/**
 * API Proxy - forwards requests to the backend API.
 * Handles token refresh inline since sessionHooks.fetch only fires on /api/_auth/session.
 */
export default defineEventHandler(async (event: H3Event) => {
  const path = event.path.replace(/^\/api\//, '')
  const target = joinURL(useRuntimeConfig().apiBase as string, 'api/v1', path)

  let session = await getUserSession(event)

  if (session.user && session.secure?.apiToken && session.secure?.refreshToken && session.tokenExpiresAt) {
    const needsRefresh = Date.now() + REFRESH_BUFFER_MS >= session.tokenExpiresAt

    if (needsRefresh) {
      try {
        const tokens = await $fetch<{
          access_token: string
          refresh_token: string
          expires_in: number
        }>(`${useRuntimeConfig().apiBase}/api/v1/auth/refresh`, {
          method: 'POST',
          body: { refresh_token: session.secure.refreshToken },
        })

        await setUserSession(event, {
          ...session,
          secure: {
            apiToken: tokens.access_token,
            refreshToken: tokens.refresh_token,
          },
          tokenExpiresAt: Date.now() + tokens.expires_in * 1000,
        })
        session = await getUserSession(event)
      } catch {
        await clearUserSession(event)
        throw createError({ statusCode: 401, statusMessage: 'Session expired' })
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
