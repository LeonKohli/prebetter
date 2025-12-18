/**
 * Shared skeleton row hint for smoother transitions.
 * When navigating to a view with known row count (e.g., clicking badge "3"),
 * set the hint so skeleton shows correct number of rows.
 *
 * Uses useState() for SSR safety - prevents state pollution between requests.
 */
export function useSkeletonHint() {
  const skeletonHint = useState<number | null>('skeleton-hint', () => null)

  function setHint(count: number) {
    skeletonHint.value = count
  }

  function clearHint() {
    skeletonHint.value = null
  }

  return {
    hint: skeletonHint,
    setHint,
    clearHint,
  }
}
