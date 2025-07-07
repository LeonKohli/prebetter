import type { UserSession } from '#auth-utils'

declare module '#auth-utils' {
  interface User {
    // Your user type from the backend API
    id: number
    email: string
    username: string
    fullName: string
    isSuperuser: boolean
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