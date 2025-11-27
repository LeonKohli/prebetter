// Shared auth types - auto-imported in both client and server contexts
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
    loggedInAt: string
    tokenExpiresAt: number // Unix timestamp (ms) when access token expires
  }

  interface SecureSessionData {
    apiToken: string
    refreshToken: string
  }
}

export {}