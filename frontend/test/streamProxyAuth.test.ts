import { beforeEach, describe, expect, it, vi } from 'vitest'

interface TestSession {
  secure?: {
    apiToken: string
    refreshToken: string
  }
  tokenExpiresAt?: number
  loggedInAt?: string
}

function createErrorStub({ statusCode, statusMessage, message }: { statusCode: number, statusMessage?: string, message?: string }) {
  const err = new Error(statusMessage || message)
  ;(err as Error & { statusCode: number; statusMessage?: string }).statusCode = statusCode
  ;(err as Error & { statusCode: number; statusMessage?: string }).statusMessage = statusMessage
  return err
}

function createEvent(session: TestSession) {
  return {
    session,
    node: {
      req: {
        on: vi.fn(),
      },
    },
  }
}

describe('stream proxy auth refresh', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.unstubAllGlobals()

    vi.stubGlobal('defineEventHandler', (fn: unknown) => fn)
    vi.stubGlobal('useRuntimeConfig', () => ({ apiBase: 'http://backend.test' }))
    vi.stubGlobal('getUserSession', vi.fn(async (event: { session: TestSession }) => structuredClone(event.session)))
    vi.stubGlobal('setUserSession', vi.fn(async (event: Record<string, unknown>, session: TestSession) => {
      event.writtenSession = structuredClone(session)
    }))
    vi.stubGlobal('clearUserSession', vi.fn(async () => {}))
    vi.stubGlobal('createError', createErrorStub)
    vi.stubGlobal('setResponseHeader', vi.fn())
    vi.stubGlobal('sendStream', vi.fn(async (_event: unknown, body: unknown) => body))
  })

  it.each([
    ['../server/api/alerts-stream.get.ts', 'http://backend.test/api/v1/alerts/stream'],
    ['../server/api/heartbeats-stream.get.ts', 'http://backend.test/api/v1/heartbeats/stream'],
  ])('refreshes the session before opening %s', async (modulePath, expectedUrl) => {
    const fetchMock = vi.fn(async (url: string, opts?: { body?: { refresh_token: string } }) => {
      if (!url.endsWith('/api/v1/auth/refresh')) throw new Error(`Unexpected refresh URL: ${url}`)

      expect(opts?.body?.refresh_token).toBe('refresh-old')
      return { access_token: 'access-new', refresh_token: 'refresh-new', expires_in: 900 }
    })

    vi.stubGlobal('$fetch', fetchMock)
    vi.stubGlobal('fetch', vi.fn(async (url: string, opts?: { headers?: Record<string, string> }) => ({
      ok: true,
      body: { url, auth: opts?.headers?.Authorization },
      status: 200,
      statusText: 'OK',
    })))

    const { default: handler } = await import(modulePath)
    const result = await handler(createEvent({
      secure: { apiToken: 'access-old', refreshToken: 'refresh-old' },
      tokenExpiresAt: Date.now() - 1000,
      loggedInAt: new Date().toISOString(),
    }))

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(result).toEqual({
      url: expectedUrl,
      auth: 'Bearer access-new',
    })
  })
})
