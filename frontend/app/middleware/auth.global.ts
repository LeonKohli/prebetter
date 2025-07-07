export default defineNuxtRouteMiddleware(async (to) => {
  // Make sure the composable already tried to fetch
  const { loggedIn, ready } = useUserSession()
  if (!ready.value) await nextTick() // tiny SSR-CSR gap guard

  // Flags come from definePageMeta()
  const needsAuth = to.meta.requiresAuth === true
  const guestOnly = to.meta.guestOnly === true

  if (needsAuth && !loggedIn.value) {
    return navigateTo(`/login?redirect=${encodeURIComponent(to.fullPath)}`)
  }
  if (guestOnly && loggedIn.value) {
    return navigateTo('/') // redirect to dashboard
  }
})