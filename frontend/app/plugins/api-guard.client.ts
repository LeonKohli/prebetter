export default defineNuxtPlugin(() => {
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