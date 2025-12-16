/**
 * Shared skeleton row hint for smoother transitions.
 * When navigating to a view with known row count (e.g., clicking badge "3"),
 * set the hint so skeleton shows correct number of rows.
 */
const skeletonHint = ref<number | null>(null)

export function useSkeletonHint() {
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
