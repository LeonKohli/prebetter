/**
 * Reactive auth state from Better Auth's session store (shared nanostore). It
 * updates on sign-in and sign-out, so components read it for live UI. Route
 * gating lives in the auth.global middleware, which reads the session fresh.
 */
export function useAuth() {
  const session = authClient.useSession()

  const user = computed(() => session.value?.data?.user ?? null)
  const loggedIn = computed(() => !!session.value?.data)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isPending = computed(() => session.value?.isPending ?? false)
  const refetch = () => session.value?.refetch()

  return { session, user, loggedIn, isAdmin, isPending, refetch }
}
