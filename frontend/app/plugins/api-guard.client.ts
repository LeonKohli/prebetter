export default defineNuxtPlugin(() => {
  // Override the global $fetch to add our interceptor
  globalThis.$fetch = $fetch.create({
    onResponseError({ response }) {
      if (response.status === 401) {
        const { clear } = useUserSession()
        clear().then(() => {
          navigateTo('/login')
        })
      }
    }
  })
})