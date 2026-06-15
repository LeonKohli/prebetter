import { createAuthClient } from 'better-auth/vue'

export default defineNuxtRouteMiddleware(async (to) => {
  const needsAuth = to.meta.requiresAuth === true
  const guestOnly = to.meta.guestOnly === true
  if (!needsAuth && !guestOnly) return

  // Read the session fresh on every navigation. useSession(useFetch) is cached
  // by Nuxt and would read a stale value right after sign-in / sign-out, which
  // bounces login back and traps logout on a protected page. On the server the
  // singleton client has no request context, so use a request-scoped client
  // that forwards the incoming cookies.
  const client = import.meta.server
    ? createAuthClient({
        baseURL: useRequestURL().origin,
        fetchOptions: { headers: useRequestHeaders(['cookie']) },
      })
    : authClient
  const { data: session } = await client.getSession()
  const loggedIn = !!session

  if (needsAuth && !loggedIn) {
    return navigateTo(`/login?redirect=${encodeURIComponent(to.fullPath)}`)
  }
  if (guestOnly && loggedIn) {
    return navigateTo('/')
  }
})
