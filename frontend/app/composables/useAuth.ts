/**
 * Reactive auth state backed by Better Auth's session store (shared nanostore).
 * The route middleware warms the store via `useSession(useFetch)` for SSR;
 * components read it synchronously here.
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
