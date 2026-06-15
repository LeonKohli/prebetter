/**
 * Redirect to /login when an in-app API call returns 401 (session expired while
 * the user is active). The route middleware already covers page loads and
 * navigations; this covers requests made from an already-rendered page — Nuxt's
 * docs and better-auth discussion #35019 recommend both layers together.
 *
 * Wrapping the global $fetch (as the published @crouton/auth plugin does) is
 * what lets this also catch useFetch, which otherwise swallows the error into
 * error.value instead of surfacing it. Client-only, so SSR and the Nitro proxy
 * keep their own untouched $fetch.
 */
export default defineNuxtPlugin((nuxtApp) => {
  let redirecting = false

  globalThis.$fetch = $fetch.create({
    onResponseError({ request, response }) {
      if (response?.status !== 401 || redirecting) return

      const url = typeof request === 'string' ? request : request.url
      // Better Auth owns its 401s (e.g. wrong password on the login form);
      // redirecting on those would loop.
      if (url.includes('/api/auth/')) return

      redirecting = true
      const redirect = window.location.pathname + window.location.search
      Promise
        .resolve(nuxtApp.runWithContext(() => navigateTo({ path: '/login', query: { redirect } })))
        .finally(() => setTimeout(() => { redirecting = false }, 2000))
    },
  }) as typeof globalThis.$fetch
})
