export default defineNitroPlugin(() => {
  // Hook to extend session data when fetched
  sessionHooks.hook('fetch', async (session, event) => {
    // The session already contains the user data we need
    // We could extend it here if needed
  })

  // Hook for when session is cleared
  sessionHooks.hook('clear', async (session, event) => {
    // Log the logout if needed
    console.log('User session cleared')
  })
})