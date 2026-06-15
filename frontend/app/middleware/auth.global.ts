export default defineNuxtRouteMiddleware(async (to) => {
  const needsAuth = to.meta.requiresAuth === true
  const guestOnly = to.meta.guestOnly === true
  if (!needsAuth && !guestOnly) return

  // SSR-safe session load; also warms the shared store for client components.
  const { data: session } = await authClient.useSession(useFetch)
  const loggedIn = !!session.value

  if (needsAuth && !loggedIn) {
    return navigateTo(`/login?redirect=${encodeURIComponent(to.fullPath)}`)
  }
  if (guestOnly && loggedIn) {
    return navigateTo('/')
  }
})
