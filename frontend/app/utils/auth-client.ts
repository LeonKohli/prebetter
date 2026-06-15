import { createAuthClient } from 'better-auth/vue'
import { usernameClient, adminClient } from 'better-auth/client/plugins'

// Auto-imported by Nuxt. Use `authClient.signIn`, `authClient.useSession`, etc.
export const authClient = createAuthClient({
  plugins: [usernameClient(), adminClient()],
})

// Inferred from the auth config (incl. username/admin plugin fields). Source of
// truth for the user shape across components — never hand-maintained.
export type AppUser = typeof authClient.$Infer.Session.user
