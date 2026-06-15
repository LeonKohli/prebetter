import { createAuthClient } from 'better-auth/vue'
import { usernameClient, adminClient } from 'better-auth/client/plugins'

// Auto-imported by Nuxt. Use `authClient.signIn`, `authClient.useSession`, etc.
export const authClient = createAuthClient({
  plugins: [usernameClient(), adminClient()],
})
