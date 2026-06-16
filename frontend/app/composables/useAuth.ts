import { createAuthClient } from 'better-auth/vue'
import type { AppUser } from '~/utils/auth-client'

type AppSession = typeof authClient.$Infer.Session.session

/**
 * Auth state in Nuxt `useState` so it is serialized from SSR and known at
 * hydration — components render the correct state immediately instead of
 * flashing logged-out while a client-only session request resolves. The route
 * middleware seeds and refreshes it via `fetchSession` on each navigation.
 */
export function useAuth() {
  const session = useState<AppSession | null>('auth:session', () => null)
  const user = useState<AppUser | null>('auth:user', () => null)
  const ready = useState('auth:ready', () => false)

  async function fetchSession() {
    // On the server the singleton client has no request context, so build a
    // request-scoped client that forwards the incoming cookies; on the client
    // the singleton already targets the current origin.
    const client = import.meta.server
      ? createAuthClient({
          baseURL: useRequestURL().origin,
          fetchOptions: { headers: useRequestHeaders(['cookie']) },
        })
      : authClient
    const { data } = await client.getSession()
    // The server response carries plugin fields (role/username) regardless of
    // the plugin-less scoped client's narrower type, so bridge it to AppUser.
    session.value = (data?.session ?? null) as AppSession | null
    user.value = (data?.user ?? null) as AppUser | null
    ready.value = true
    return data
  }

  return {
    session,
    user,
    loggedIn: computed(() => !!session.value),
    isAdmin: computed(() => user.value?.role === 'admin'),
    isPending: computed(() => !ready.value),
    refetch: fetchSession,
    fetchSession,
  }
}
