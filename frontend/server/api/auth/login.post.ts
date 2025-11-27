export default defineEventHandler(async (event) => {
  const { username, password } = await readBody(event)

  if (!username || !password) {
    throw createError({ statusCode: 400, message: 'Missing username or password' })
  }

  const { apiBase } = useRuntimeConfig()

  try {
    // Get both access and refresh tokens from backend
    const tokens = await $fetch<{
      access_token: string
      refresh_token: string
      expires_in: number
    }>(`${apiBase}/api/v1/auth/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({ username, password }).toString(),
    })

    // Get user info with the new access token
    const userInfo = await $fetch<{
      id: string
      email: string
      username: string
      full_name: string | null
      is_superuser: boolean
    }>(`${apiBase}/api/v1/auth/users/me`, {
      headers: {
        'Authorization': `Bearer ${tokens.access_token}`,
      },
    })

    // Calculate when access token expires
    const tokenExpiresAt = Date.now() + tokens.expires_in * 1000

    await setUserSession(event, {
      user: {
        id: userInfo.id,
        email: userInfo.email,
        username: userInfo.username,
        full_name: userInfo.full_name,
        is_superuser: userInfo.is_superuser,
      },
      // Both tokens stored server-side only for security
      secure: {
        apiToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
      },
      loggedInAt: new Date().toISOString(),
      tokenExpiresAt,
    })

    return { success: true }
  } catch (error: unknown) {
    console.error('[Login Error]', error)
    throw createError({
      statusCode: 401,
      statusMessage: 'Invalid username or password',
    })
  }
})