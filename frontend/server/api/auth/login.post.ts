export default defineEventHandler(async (event) => {
  const { username, password } = await readBody(event)
  
  if (!username || !password) {
    throw createError({ statusCode: 400, message: 'Missing username or password' })
  }

  const { apiBase } = useRuntimeConfig()
  
  try {
    // 1. Authenticate with your backend to get the JWT
    const tokens = await $fetch<{ access_token: string }>(`${apiBase}/api/v1/auth/token`, {
      method: 'POST',
      body: new URLSearchParams({ username, password }),
    })

    const accessToken = tokens.access_token

    // 2. Fetch user information from the backend using the new token
    const userInfo = await $fetch<{
      id: number
      email: string
      username: string
      full_name: string
      is_superuser: boolean
    }>(`${apiBase}/api/v1/auth/users/me`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    })

    // 3. Set the session using nuxt-auth-utils
    await setUserSession(event, {
      user: {
        id: userInfo.id,
        email: userInfo.email,
        username: userInfo.username,
        fullName: userInfo.full_name,
        isSuperuser: userInfo.is_superuser,
      },
      // Store the token in the 'secure' part of the session.
      // It will only be available on the server, not exposed to the client.
      secure: {
        apiToken: accessToken,
      },
      loggedInAt: new Date().toISOString(),
    })

    return { success: true }
  } catch (error: any) {
    // Log the error for debugging
    console.error('[Login Error]', error)
    
    // Throw a generic, user-friendly error
    throw createError({
      statusCode: 401,
      statusMessage: 'Invalid username or password'
    })
  }
})