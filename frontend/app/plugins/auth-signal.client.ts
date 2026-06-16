/**
 * Mirrors Better Auth's reactive session signal into our useState session.
 *
 * The client toggles `$sessionSignal` after every self-session mutation —
 * sign-in (incl. username), sign-out, update-user, change-password/email
 * (see better-auth `config.mjs` atomListeners + the username plugin). Listening
 * to it keeps the navbar and guarded UI in sync without waiting for the next
 * navigation, so call sites no longer need manual refetch nudges.
 *
 * `$store.listen` fires once immediately (a harmless re-confirm at startup) and
 * then on every toggle; we refetch on each, ignoring the signal value.
 */
export default defineNuxtPlugin((nuxtApp) => {
  const { fetchSession } = useAuth()
  authClient.$store.listen('$sessionSignal', () => {
    nuxtApp.runWithContext(() => fetchSession())
  })
})
