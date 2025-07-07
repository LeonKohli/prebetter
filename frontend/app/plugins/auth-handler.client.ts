export default defineNuxtPlugin((nuxtApp) => {
  const { clear } = useUserSession()
  
  // Intercept all fetch errors
  nuxtApp.hook('app:error', (error) => {
    // Check if it's a 401 error
    if (error.statusCode === 401 || error.message?.includes('401')) {
      clear().then(() => {
        navigateTo('/login?reason=session-expired')
      })
    }
  })
  
  // Also handle vue errors that might contain 401
  nuxtApp.vueApp.config.errorHandler = (error: any) => {
    if (error.statusCode === 401 || error.data?.statusCode === 401) {
      clear().then(() => {
        navigateTo('/login?reason=session-expired')
      })
    }
  }
})