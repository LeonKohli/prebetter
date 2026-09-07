import { randomUUID } from 'node:crypto'
import { createServer } from 'node:http'
import { once } from 'node:events'
import { fileURLToPath } from 'node:url'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { setup, $fetch, url } from '@nuxt/test-utils/e2e'
import { createPool } from 'mysql2/promise'
import { createRemoteJWKSet, jwtVerify } from 'jose'

// These tests write users and sessions. Require an explicitly selected test DB.
if (!process.env.MYSQL_PREBETTER_DB?.endsWith('_test')) {
  throw new Error('MYSQL_PREBETTER_DB must name a disposable database ending in _test')
}

const origin = 'http://127.0.0.1:43017'
process.env.BETTER_AUTH_URL = origin
process.env.BETTER_AUTH_SECRET = randomUUID() + randomUUID()
const jwks = createRemoteJWKSet(new URL('/api/auth/jwks', origin))
const backend = createServer(async (request, response) => {
  try {
    const token = request.headers.authorization?.replace(/^Bearer /, '') ?? ''
    const { payload } = await jwtVerify(token, jwks, { issuer: origin, audience: origin })
    if (request.url?.includes('/stream')) {
      response.writeHead(200, { 'Content-Type': 'text/event-stream' })
      response.end(`data: ${JSON.stringify({ userId: payload.sub })}\n\n`)
      return
    }
    if (request.url?.includes('/failure')) {
      response.writeHead(503, { 'Content-Type': 'application/json' })
      response.end(JSON.stringify({ detail: 'Backend unavailable' }))
      return
    }
    response.writeHead(200, { 'Content-Type': 'application/json' })
    response.end(JSON.stringify({ userId: payload.sub, path: request.url }))
  } catch {
    response.writeHead(401, { 'Content-Type': 'application/json' })
    response.end(JSON.stringify({ detail: 'Unauthorized' }))
  }
})
backend.listen(0, '127.0.0.1')
await once(backend, 'listening')
const address = backend.address()
if (!address || typeof address === 'string') throw new Error('Missing backend port')
const apiBase = `http://127.0.0.1:${address.port}`

const pool = createPool({
  host: process.env.MYSQL_HOST,
  port: Number(process.env.MYSQL_PORT),
  user: process.env.MYSQL_USER,
  password: process.env.MYSQL_PASSWORD,
  database: process.env.MYSQL_PREBETTER_DB,
})
const suffix = randomUUID().slice(0, 8)
const password = randomUUID()
const users: Array<{ id: string; username: string }> = []

async function signIn(username: string, suppliedPassword = password) {
  return fetch(url('/api/auth/sign-in/username'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Origin: origin },
    body: JSON.stringify({ username, password: suppliedPassword }),
  })
}

async function loginCookie(username: string) {
  const response = await signIn(username)
  expect(response.status).toBe(200)
  const cookie = response.headers.getSetCookie()
    .map(value => value.split(';')[0]).join('; ')
  expect(cookie).toContain('session_token=')
  return cookie
}

describe('Better Auth and API proxies', async () => {
  await setup({
    rootDir: fileURLToPath(new URL('../..', import.meta.url)),
    port: 43017,
    browser: false,
    env: { ...process.env, NUXT_API_BASE: apiBase },
    nuxtConfig: { runtimeConfig: { apiBase }, devtools: { enabled: false } },
  })

  beforeAll(async () => {
    // Signing keys are encrypted with this run's temporary auth secret.
    await pool.execute('DELETE FROM `jwks`')
    const { auth } = await import('../../server/utils/auth')
    for (const name of ['alice', 'bob']) {
      const username = `${name}_${suffix}`
      const { user } = await auth.api.createUser({
        body: { name: username, email: `${username}@example.com`, password, data: { username } },
      })
      users.push({ id: user.id, username })
    }
  })

  afterAll(async () => {
    for (const user of users) {
      await pool.execute('DELETE FROM `session` WHERE userId = ?', [user.id])
      await pool.execute('DELETE FROM `account` WHERE userId = ?', [user.id])
      await pool.execute('DELETE FROM `user` WHERE id = ?', [user.id])
    }
    await pool.execute('DELETE FROM `jwks`')
    await pool.end()
    backend.closeAllConnections()
    await new Promise<void>((resolve, reject) => backend.close(error => error ? reject(error) : resolve()))
  })

  it('rejects missing credentials and incorrect passwords', async () => {
    const missing = await fetch(url('/api/auth/sign-in/username'), {
      method: 'POST', headers: { 'Content-Type': 'application/json', Origin: origin }, body: '{}',
    })
    expect(missing.status).toBe(400)
    expect((await signIn(users[0]!.username, randomUUID())).status).toBe(401)
  })

  it('keeps public registration closed', async () => {
    const response = await fetch(url('/api/auth/sign-up/email'), {
      method: 'POST', headers: { 'Content-Type': 'application/json', Origin: origin },
      body: JSON.stringify({ name: 'Stranger', email: `stranger_${suffix}@example.com`, password }),
    })
    expect(response.status).toBe(400)
  })

  it('returns no session and rejects protected requests without a cookie', async () => {
    expect(await $fetch('/api/auth/get-session')).toBeNull()
    for (const path of ['/api/alerts/', '/api/alerts-stream', '/api/heartbeats-stream']) {
      expect((await fetch(url(path))).status).toBe(401)
    }
  })

  it('isolates concurrent requests from two sessions and preserves query parameters', async () => {
    const cookies = await Promise.all(users.map(user => loginCookie(user.username)))
    const results = await Promise.all(cookies.map(cookie =>
      $fetch<{ userId: string; path: string }>('/api/alerts/?classification=%E6%B5%8B%E8%AF%95', { headers: { cookie } }),
    ))
    expect(results.map(result => result.userId)).toEqual(users.map(user => user.id))
    expect(results[0].path).toBe('/api/v1/alerts/?classification=%E6%B5%8B%E8%AF%95')
    const sameSession = await Promise.all([0, 1].map(() =>
      $fetch<{ userId: string }>('/api/alerts/', { headers: { cookie: cookies[0]! } }),
    ))
    expect(sameSession.map(result => result.userId)).toEqual([users[0]!.id, users[0]!.id])
  })

  it.each(['/api/alerts-stream', '/api/heartbeats-stream'])('authenticates %s', async (path) => {
    const cookie = await loginCookie(users[0]!.username)
    const response = await fetch(url(path), { headers: { cookie } })
    expect(response.status).toBe(200)
    expect(response.headers.get('content-type')).toContain('text/event-stream')
    expect(await response.text()).toBe(`data: ${JSON.stringify({ userId: users[0]!.id })}\n\n`)
  })

  it('preserves backend service errors', async () => {
    const cookie = await loginCookie(users[0]!.username)
    const response = await fetch(url('/api/failure'), { headers: { cookie } })
    expect(response.status).toBe(503)
    expect(await response.json()).toEqual({ detail: 'Backend unavailable' })
  })

  it('invalidates a signed-out session for ordinary and streaming requests', async () => {
    const cookie = await loginCookie(users[0]!.username)
    const session = await $fetch<{ user: { id: string } }>('/api/auth/get-session', { headers: { cookie } })
    expect(session.user.id).toBe(users[0]!.id)
    const response = await fetch(url('/api/auth/sign-out'), {
      method: 'POST', headers: { cookie, Origin: origin, 'Content-Type': 'application/json' }, body: '{}',
    })
    expect(response.status).toBe(200)
    for (const path of ['/api/alerts/', '/api/alerts-stream', '/api/heartbeats-stream']) {
      expect((await fetch(url(path), { headers: { cookie } })).status).toBe(401)
    }
  })
})
