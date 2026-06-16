/**
 * Decides what a give-up'd SSE stream means for auth.
 *
 * A native EventSource error carries no HTTP status (WHATWG spec) — VueUse only
 * surfaces `readyState`, so we can't tell a 401 from a network blip at the SSE
 * layer. When auto-reconnect exhausts its retries we therefore ask the session
 * endpoint directly: if the session is gone the failures were an expired or
 * revoked session → redirect to login (the same guarded path the route
 * middleware and the api-401 plugin use). If the session is still valid the
 * backend was merely unreachable, not an auth problem → stay put and let the
 * stream keep trying.
 */
export function useSseSessionGuard() {
  const nuxtApp = useNuxtApp()
  const { fetchSession, loggedIn } = useAuth()

  return async function onSseGiveUp() {
    await fetchSession()
    if (loggedIn.value) return
    const redirect = window.location.pathname + window.location.search
    await nuxtApp.runWithContext(() =>
      navigateTo({ path: '/login', query: { redirect } }),
    )
  }
}
