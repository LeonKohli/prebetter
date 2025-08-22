export default defineEventHandler(async (event) => {
  const { username, password } = await readBody(event)
  
  if (!username || !password) {
    throw createError({ statusCode: 400, message: 'Missing username or password' })
  }

  const { apiBase } = useRuntimeConfig()
  
  try {
    const tokens = await $fetch<{ access_token: string }>(`${apiBase}/api/v1/auth/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({ username, password }).toString(),
    })

    const accessToken = tokens.access_token

    const userInfo = await $fetch<{
      id: string
      email: string
      username: string
      full_name: string | null
      is_superuser: boolean
    }>(`${apiBase}/api/v1/auth/users/me`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    })

    await setUserSession(event, {
      user: {
        id: userInfo.id,
        email: userInfo.email,
        username: userInfo.username,
        full_name: userInfo.full_name,
        is_superuser: userInfo.is_superuser,
      },
      // Token stored server-side only for security
      secure: {
        apiToken: accessToken,
      },
      loggedInAt: new Date().toISOString(),
    })

    return { success: true }
  } catch (error: any) {
    console.error('[Login Error]', error)
    throw createError({
      statusCode: 401,
      statusMessage: 'Invalid username or password'
    })
  }
})