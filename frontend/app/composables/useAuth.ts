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
    // useRequestFetch() is Nuxt's primitive for an SSR-authenticated request: on
    // the server it forwards the incoming cookies and the relative URL resolves
    // to an in-process Nitro call (no public-origin round trip); on the client
    // it is a plain $fetch using the browser's cookies. This is what makes the
    // session known at SSR so the navbar/guard never flash logged-out.
    const data = await useRequestFetch()<{ session: AppSession; user: AppUser } | null>(
      '/api/auth/get-session',
    )
    session.value = data?.session ?? null
    user.value = data?.user ?? null
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
