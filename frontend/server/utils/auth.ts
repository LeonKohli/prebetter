import { betterAuth } from 'better-auth'
import { createAuthMiddleware, APIError } from 'better-auth/api'
import { createPool } from 'mysql2/promise'
import { username, admin, jwt } from 'better-auth/plugins'
import bcrypt from 'bcryptjs'

const baseURL = process.env.BETTER_AUTH_URL || 'http://localhost:3000'

export const auth = betterAuth({
  baseURL,
  secret: process.env.BETTER_AUTH_SECRET,
  database: createPool({
    host: process.env.MYSQL_HOST,
    port: Number(process.env.MYSQL_PORT ?? 3306),
    user: process.env.MYSQL_USER,
    password: process.env.MYSQL_PASSWORD,
    database: process.env.MYSQL_PREBETTER_DB,
  }),
  emailAndPassword: {
    enabled: true,
    // Admin-managed users only: no public self-registration. Accounts are
    // created via the admin plugin (auth.api.createUser), which bypasses sign-up.
    disableSignUp: true,
    // Bridge to the existing bcrypt hashes so migrated users keep their passwords.
    password: {
      hash: (password) => bcrypt.hash(password, 12),
      verify: ({ hash, password }) => bcrypt.compare(password, hash),
    },
  },
  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days, matches the previous refresh-token lifetime
  },
  hooks: {
    // Block removing or demoting the last administrator (admin plugin has no such guard).
    before: createAuthMiddleware(async (ctx) => {
      if (ctx.path !== '/admin/remove-user' && ctx.path !== '/admin/set-role') return

      const userId = ctx.body?.userId as string | undefined
      if (!userId) return

      const target = await ctx.context.adapter.findOne<{ role?: string | null }>({
        model: 'user',
        where: [{ field: 'id', value: userId }],
      })
      if (target?.role !== 'admin') return

      // Keeping admin role on set-role is fine; only guard demotion or removal.
      if (ctx.path === '/admin/set-role') {
        const role = ctx.body?.role
        const roles = Array.isArray(role) ? role : [role]
        if (roles.includes('admin')) return
      }

      const adminCount = await ctx.context.adapter.count({
        model: 'user',
        where: [{ field: 'role', value: 'admin' }],
      })
      if (adminCount <= 1) {
        throw new APIError('BAD_REQUEST', {
          message: 'Cannot remove or demote the last administrator',
        })
      }
    }),
  },
  plugins: [
    username(),
    admin(),
    jwt({
      jwt: {
        issuer: baseURL,
        audience: baseURL,
        expirationTime: '15m',
        // `sub` defaults to user.id; carry the claims FastAPI needs to authorize.
        definePayload: ({ user }) => ({
          email: (user as { email: string }).email,
          username: (user as { username?: string }).username,
          role: (user as { role?: string }).role,
        }),
      },
    }),
  ],
})
