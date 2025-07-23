export default defineNuxtRouteMiddleware((to) => {
  const { loggedIn, ready } = useUserSession()
  
  // Skip during SSR to avoid hydration mismatches
  if (!ready.value) {
    return
  }

  const needsAuth = to.meta.requiresAuth === true
  const guestOnly = to.meta.guestOnly === true

  if (needsAuth && !loggedIn.value) {
    return navigateTo(`/login?redirect=${encodeURIComponent(to.fullPath)}`)
  }
  if (guestOnly && loggedIn.value) {
    return navigateTo('/')
  }
})