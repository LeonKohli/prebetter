import { beforeEach, describe, expect, it, vi } from 'vitest'

function createErrorStub({ statusCode, statusMessage, message }: { statusCode: number, statusMessage?: string, message?: string }) {
  const err = new Error(statusMessage || message)
  ;(err as Error & { statusCode: number; statusMessage?: string }).statusCode = statusCode
  ;(err as Error & { statusCode: number; statusMessage?: string }).statusMessage = statusMessage
  return err
}

describe('login handler error mapping', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.unstubAllGlobals()

    vi.stubGlobal('defineEventHandler', (fn: unknown) => fn)
    vi.stubGlobal('readBody', vi.fn(async () => ({ username: 'admin', password: 'admin' })))
    vi.stubGlobal('useRuntimeConfig', () => ({ apiBase: 'http://backend.test' }))
    vi.stubGlobal('setUserSession', vi.fn(async () => {}))
    vi.stubGlobal('createError', createErrorStub)
  })

  it('returns 503 when the backend auth service is unavailable', async () => {
    const fetchMock = vi.fn(async () => {
      const err = new Error('connect ECONNREFUSED 127.0.0.1:8000') as Error & { statusCode?: number; cause?: Error }
      err.statusCode = 503
      err.cause = new Error('ECONNREFUSED')
      throw err
    })

    vi.stubGlobal('$fetch', fetchMock)

    const { default: handler } = await import('../server/api/auth/login.post.ts')

    await expect(handler({})).rejects.toMatchObject({
      statusCode: 503,
      statusMessage: 'Authentication service unavailable',
    })
  })

  it('returns 401 only for invalid credentials', async () => {
    const fetchMock = vi.fn(async () => {
      const err = new Error('Unauthorized') as Error & { statusCode?: number; statusMessage?: string }
      err.statusCode = 401
      err.statusMessage = 'Unauthorized'
      throw err
    })

    vi.stubGlobal('$fetch', fetchMock)

    const { default: handler } = await import('../server/api/auth/login.post.ts')

    await expect(handler({})).rejects.toMatchObject({
      statusCode: 401,
      statusMessage: 'Invalid username or password',
    })
  })
})
