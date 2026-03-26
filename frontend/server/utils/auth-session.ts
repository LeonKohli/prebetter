import type { H3Event } from 'h3'

const REFRESH_BUFFER_MS = 2 * 60 * 1000 // Refresh 2 min before expiry

type RefreshedTokens = {
  apiToken: string
  refreshToken: string
  expiresAt: number
}

// Deduplicate only identical refresh attempts. Different user sessions must never
// share refreshed tokens, even within the same server process.
const inFlightRefreshes = new Map<string, Promise<RefreshedTokens>>()

export async function getSessionWithFreshTokens(event: H3Event) {
  let session = await getUserSession(event)

  if (session.secure?.apiToken && session.secure?.refreshToken && session.tokenExpiresAt) {
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

  return session
}
