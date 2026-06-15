import { betterAuth } from 'better-auth'
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
    // Bridge to the existing bcrypt hashes so migrated users keep their passwords.
    password: {
      hash: (password) => bcrypt.hash(password, 12),
      verify: ({ hash, password }) => bcrypt.compare(password, hash),
    },
  },
  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days, matches the previous refresh-token lifetime
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
