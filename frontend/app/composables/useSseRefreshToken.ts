/**
 * Shared SSE refresh token for coordinating updates between components.
 * When SSE receives new alerts, bump this token to trigger refetches
 * in all components that depend on it.
 *
 * Uses useState() for SSR safety - prevents state pollution between requests.
 */
export function useSseRefreshToken() {
  const sseRefreshToken = useState<number>('sse-refresh-token', () => 0)

  function bump() {
    sseRefreshToken.value = Date.now()
  }

  return {
    token: sseRefreshToken,
    bump,
  }
}
