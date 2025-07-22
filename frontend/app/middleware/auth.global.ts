export default defineNuxtRouteMiddleware((to) => {
  const { loggedIn, ready } = useUserSession()
  
  // Skip middleware during SSR or if session is not ready yet
  // The session will be properly hydrated during client-side initialization
  if (!ready.value) {
    return
  }

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