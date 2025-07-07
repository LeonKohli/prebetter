declare module '#auth-utils' {
  interface User {
    id: number
    email: string
    username: string
    fullName?: string
    isSuperuser: boolean
  }

  interface UserSession {
    user: User
    loggedInAt: string
  }

  interface SecureSessionData {
    apiToken: string
  }
}

export {}