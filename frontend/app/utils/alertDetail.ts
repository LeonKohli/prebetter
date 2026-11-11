/** First 12 characters of the 64-character event id, enough to tell alerts apart on screen. */
export function shortAlertId(id: string): string {
  return id.slice(0, 12)
}

/** Public Snort rule documentation for a `gid:sid` rule id, or undefined when the id has another shape. */
export function snortRuleDocUrl(ruleId?: string | null): string | undefined {
  const match = ruleId?.match(/^(\d+):(\d+)$/)
  return match ? `https://www.snort.org/rule_docs/${match[1]}-${match[2]}` : undefined
}
