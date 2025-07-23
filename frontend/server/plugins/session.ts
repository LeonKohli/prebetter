export default defineNitroPlugin(() => {
  sessionHooks.hook('fetch', async (session, event) => {
    if (!session.user || !session.secure?.apiToken) {
      return
    }

    const { apiBase } = useRuntimeConfig()
    
    try {
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

      session.user = {
        id: userInfo.id,
        email: userInfo.email,
        username: userInfo.username,
        full_name: userInfo.full_name,
        is_superuser: userInfo.is_superuser,
      }
    } catch (error) {
      console.error('[Session Fetch Hook Error]', error)
    }
  })

  sessionHooks.hook('clear', async (session, event) => {
    console.log('User session cleared')
  })
})