import type { UserSession } from '#auth-utils'

declare module '#auth-utils' {
  interface User {
    // Backend API format - no conversion
    id: string
    email: string
    username: string
    full_name?: string | null
    is_superuser: boolean
  }

  interface UserSession {
    // Add any custom fields you want to store in the session
    loggedInAt: string
  }

  interface SecureSessionData {
    // This is where we'll securely store the JWT
    apiToken: string
  }
}

export {}