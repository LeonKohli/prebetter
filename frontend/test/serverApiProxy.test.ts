import { beforeEach, describe, expect, it, vi } from 'vitest'

interface TestSession {
  user?: { id: string }
  secure?: {
    apiToken: string
    refreshToken: string
  }
  tokenExpiresAt?: number
}

function createErrorStub({ statusCode, statusMessage, message }: { statusCode: number, statusMessage?: string, message?: string }) {
  const err = new Error(statusMessage || message)
  ;(err as Error & { statusCode: number; statusMessage?: string }).statusCode = statusCode
  ;(err as Error & { statusCode: number; statusMessage?: string }).statusMessage = statusMessage
  return err
}

function createEvent(session: TestSession) {
  return {
    path: '/api/alerts',
    method: 'GET',
    session,
  }
}

describe('server api proxy refresh handling', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.unstubAllGlobals()

    vi.stubGlobal('defineEventHandler', (fn: unknown) => fn)
    vi.stubGlobal('useRuntimeConfig', () => ({ apiBase: 'http://backend.test' }))
    vi.stubGlobal('getUserSession', vi.fn(async (event: { session: TestSession }) => structuredClone(event.session)))
    vi.stubGlobal('setUserSession', vi.fn(async (event: Record<string, unknown>, session: TestSession) => {
      event.writtenSession = structuredClone(session)
    }))
    vi.stubGlobal('clearUserSession', vi.fn(async (event: Record<string, unknown>) => {
      event.cleared = true
    }))
    vi.stubGlobal('getRequestHeader', vi.fn((_event: unknown, name: string) => name === 'accept' ? 'application/json' : undefined))
    vi.stubGlobal('createError', createErrorStub)
  })

  it('does not share refreshed tokens across different sessions', async () => {
    const refreshCalls: string[] = []
    const rawCalls: Array<{ auth: string | undefined }> = []

    const fetchMock = vi.fn(async (url: string, opts?: { body?: { refresh_token: string } }) => {
      if (!url.endsWith('/api/v1/auth/refresh')) throw new Error(`Unexpected refresh URL: ${url}`)

      const refreshToken = opts?.body?.refresh_token
      refreshCalls.push(refreshToken || '')

      if (refreshToken === 'r1') {
        return { access_token: 'a1-new', refresh_token: 'r1-new', expires_in: 900 }
      }
      if (refreshToken === 'r2') {
        return { access_token: 'a2-new', refresh_token: 'r2-new', expires_in: 900 }
      }

      throw new Error(`Unexpected refresh token: ${refreshToken}`)
    })

    fetchMock.raw = vi.fn(async (_url: string, opts?: { headers?: { Authorization?: string } }) => {
      rawCalls.push({ auth: opts?.headers?.Authorization })
      return { _data: { auth: opts?.headers?.Authorization } }
    })

    vi.stubGlobal('$fetch', fetchMock)

    const { default: handler } = await import('../server/api/[...].ts')
    const expired = Date.now() - 1000

    const event1 = createEvent({
      user: { id: 'u1' },
      secure: { apiToken: 'a1-old', refreshToken: 'r1' },
      tokenExpiresAt: expired,
    })
    const event2 = createEvent({
      user: { id: 'u2' },
      secure: { apiToken: 'a2-old', refreshToken: 'r2' },
      tokenExpiresAt: expired,
    })

    const result1 = await handler(event1)
    const result2 = await handler(event2)

    expect(refreshCalls).toEqual(['r1', 'r2'])
    expect(rawCalls).toEqual([
      { auth: 'Bearer a1-new' },
      { auth: 'Bearer a2-new' },
    ])
    expect(result1).toEqual({ auth: 'Bearer a1-new' })
    expect(result2).toEqual({ auth: 'Bearer a2-new' })
    expect((event1 as Record<string, unknown>).writtenSession).toBeTruthy()
    expect((event2 as Record<string, unknown>).writtenSession).toBeTruthy()
  })

  it('deduplicates concurrent refreshes for the same refresh token', async () => {
    const rawCalls: Array<{ auth: string | undefined }> = []
    let releaseRefresh!: () => void
    const refreshGate = new Promise<void>((resolve) => {
      releaseRefresh = resolve
    })

    const fetchMock = vi.fn(async (url: string, opts?: { body?: { refresh_token: string } }) => {
      if (!url.endsWith('/api/v1/auth/refresh')) throw new Error(`Unexpected refresh URL: ${url}`)

      expect(opts?.body?.refresh_token).toBe('shared-refresh')
      await refreshGate
      return { access_token: 'shared-new', refresh_token: 'shared-refresh-next', expires_in: 900 }
    })

    fetchMock.raw = vi.fn(async (_url: string, opts?: { headers?: { Authorization?: string } }) => {
      rawCalls.push({ auth: opts?.headers?.Authorization })
      return { _data: { auth: opts?.headers?.Authorization } }
    })

    vi.stubGlobal('$fetch', fetchMock)

    const { default: handler } = await import('../server/api/[...].ts')
    const expired = Date.now() - 1000
    const sharedSession = {
      user: { id: 'same-user' },
      secure: { apiToken: 'old-token', refreshToken: 'shared-refresh' },
      tokenExpiresAt: expired,
    }

    const requestA = handler(createEvent(sharedSession))
    const requestB = handler(createEvent(sharedSession))

    await Promise.resolve()
    releaseRefresh()

    const [resultA, resultB] = await Promise.all([requestA, requestB])

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(rawCalls).toEqual([
      { auth: 'Bearer shared-new' },
      { auth: 'Bearer shared-new' },
    ])
    expect(resultA).toEqual({ auth: 'Bearer shared-new' })
    expect(resultB).toEqual({ auth: 'Bearer shared-new' })
  })
})
