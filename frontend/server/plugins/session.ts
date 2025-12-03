const REFRESH_BUFFER_MS = 2 * 60 * 1000 // Refresh 2 min before expiry

export default defineNitroPlugin(() => {
  sessionHooks.hook('fetch', async (session, event) => {
    if (!session.user || !session.secure?.apiToken || !session.secure?.refreshToken) return

    const needsRefresh = session.tokenExpiresAt && Date.now() + REFRESH_BUFFER_MS >= session.tokenExpiresAt
    if (!needsRefresh) return

    try {
      const tokens = await $fetch<{
        access_token: string
        refresh_token: string
        expires_in: number
      }>(`${useRuntimeConfig().apiBase}/api/v1/auth/refresh`, {
        method: 'POST',
        body: { refresh_token: session.secure.refreshToken },
      })

      session.secure.apiToken = tokens.access_token
      session.secure.refreshToken = tokens.refresh_token
      session.tokenExpiresAt = Date.now() + tokens.expires_in * 1000
      await setUserSession(event, session)
    } catch {
      await clearUserSession(event)
    }
  })
})