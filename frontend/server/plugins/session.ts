export default defineNitroPlugin(() => {
  // Hook to refresh user data when session.fetch() is called
  sessionHooks.hook('fetch', async (session, event) => {
    // Only refresh if we have a user and API token
    if (!session.user || !session.secure?.apiToken) {
      return
    }

    const { apiBase } = useRuntimeConfig()
    
    try {
      // Fetch fresh user information from the backend
      const userInfo = await $fetch<{
        id: string
        email: string
        username: string
        full_name: string | null
        is_superuser: boolean
      }>(`${apiBase}/api/v1/auth/users/me`, {
        headers: {
          'Authorization': `Bearer ${session.secure.apiToken}`,
        },
      })

      // Update only the user portion of the session
      session.user = {
        id: userInfo.id,
        email: userInfo.email,
        username: userInfo.username,
        full_name: userInfo.full_name,
        is_superuser: userInfo.is_superuser,
      }
    } catch (error) {
      console.error('[Session Fetch Hook Error]', error)
      // Don't throw here - let the session continue with existing data
    }
  })

  // Hook for when session is cleared
  sessionHooks.hook('clear', async (session, event) => {
    console.log('User session cleared')
  })
})