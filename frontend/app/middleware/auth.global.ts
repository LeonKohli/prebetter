export default defineNuxtRouteMiddleware(async (to) => {
  const needsAuth = to.meta.requiresAuth === true
  const guestOnly = to.meta.guestOnly === true
  if (!needsAuth && !guestOnly) return

  // Seed and refresh the shared session. On SSR this populates useState so the
  // client hydrates already knowing the session (no logged-out flash); on the
  // client it keeps the guard fresh after sign-in / sign-out, with no cached
  // value to bounce login back or trap logout on a protected page.
  const { loggedIn, fetchSession } = useAuth()
  await fetchSession()

  if (needsAuth && !loggedIn.value) {
    return navigateTo(`/login?redirect=${encodeURIComponent(to.fullPath)}`)
  }
  if (guestOnly && loggedIn.value) {
    return navigateTo('/')
  }
})
