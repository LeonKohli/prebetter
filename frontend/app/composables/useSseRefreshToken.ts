/**
 * Shared SSE refresh token for coordinating updates between components.
 * When SSE receives new alerts, bump this token to trigger refetches
 * in all components that depend on it.
 */
const sseRefreshToken = ref(0)

export function useSseRefreshToken() {
  function bump() {
    sseRefreshToken.value = Date.now()
  }

  return {
    token: sseRefreshToken,
    bump,
  }
}
