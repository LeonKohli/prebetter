import type { H3Event } from 'h3'

const REFRESH_BUFFER_MS = 2 * 60 * 1000 // Refresh 2 min before expiry

/**
 * Ensures the session has a valid (non-expired) access token.
 * Refreshes the token if it's about to expire.
 *
 * @returns The current valid apiToken, or throws 401 if refresh fails
 */
export async function ensureValidToken(event: H3Event): Promise<string> {
  let session = await getUserSession(event)

  if (!session.secure?.apiToken) {
    throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
  }

  // Check if token needs refresh
  if (session.user && session.secure.refreshToken && session.tokenExpiresAt) {
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

  return session.secure!.apiToken
}
