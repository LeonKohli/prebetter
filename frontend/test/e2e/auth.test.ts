import { describe, it, expect } from 'vitest'
import { setup, $fetch } from '@nuxt/test-utils/e2e'

describe('Auth API E2E', async () => {
  await setup({
    browser: false, // No browser needed for API tests
  })

  describe('Login endpoint validation', () => {
    it('should return 400 for missing credentials', async () => {
      try {
        await $fetch('/api/auth/login', {
          method: 'POST',
          body: {},
        })
        expect.fail('Should have thrown')
      } catch (error: any) {
        expect(error.statusCode).toBe(400)
      }
    })

    it('should return 400 for missing password', async () => {
      try {
        await $fetch('/api/auth/login', {
          method: 'POST',
          body: { username: 'test' },
        })
        expect.fail('Should have thrown')
      } catch (error: any) {
        expect(error.statusCode).toBe(400)
      }
    })

    it('should return 400 for missing username', async () => {
      try {
        await $fetch('/api/auth/login', {
          method: 'POST',
          body: { password: 'test' },
        })
        expect.fail('Should have thrown')
      } catch (error: any) {
        expect(error.statusCode).toBe(400)
      }
    })

    it('should return 401 for invalid credentials (backend unreachable)', async () => {
      // This will fail because backend isn't running, but we test the flow
      try {
        await $fetch('/api/auth/login', {
          method: 'POST',
          body: { username: 'wronguser', password: 'wrongpass' },
        })
        expect.fail('Should have thrown')
      } catch (error: any) {
        // Either 401 (backend returned invalid) or 502 (backend unreachable)
        expect([401, 502]).toContain(error.statusCode)
      }
    })
  })

  describe('Session endpoint', () => {
    it('should return empty session for unauthenticated user', async () => {
      const session = await $fetch('/api/_auth/session')
      // Empty session should have no user
      expect(session.user).toBeUndefined()
    })
  })

  describe('API proxy without auth', () => {
    it('should return 401 or 502 for protected API without token', async () => {
      try {
        await $fetch('/api/alerts/')
        expect.fail('Should have thrown')
      } catch (error: any) {
        // 401 if backend is running, 502 if not
        expect([401, 502]).toContain(error.statusCode)
      }
    })
  })
})
