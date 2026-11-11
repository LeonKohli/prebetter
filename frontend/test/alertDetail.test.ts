import { describe, expect, it } from 'vitest'
import { shortAlertId, snortRuleDocUrl } from '../app/utils/alertDetail'

describe('shortAlertId', () => {
  it('keeps the first 12 characters of the event id', () => {
    expect(shortAlertId('0123456789abcdef0123456789abcdef')).toBe('0123456789ab')
  })
})

describe('snortRuleDocUrl', () => {
  it('links gid:sid to the Snort rule documentation', () => {
    expect(snortRuleDocUrl('1:41420')).toBe('https://www.snort.org/rule_docs/1-41420')
  })

  it.each([undefined, null, '', '41420', '1:abc', '1:41420:2'])('returns undefined for %j', (id) => {
    expect(snortRuleDocUrl(id)).toBeUndefined()
  })
})
