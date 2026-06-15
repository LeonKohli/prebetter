/**
 * One-time migration: existing `users` rows -> Better Auth `user` + `account`.
 *
 * Preserves the existing bcrypt hashes (no password reset). Idempotent: rows
 * already present in `user` (by id) are skipped. The old `users` table is left
 * intact for verification and dropped in a later step.
 *
 * Run: bun run scripts/migrate-users.ts   (env loaded from .env)
 */
import { createPool } from 'mysql2/promise'
import { randomUUID } from 'node:crypto'

type LegacyUser = {
  id: string
  email: string
  username: string
  full_name: string | null
  hashed_password: string
  is_superuser: number
  created_at: Date
  updated_at: Date | null
}

const pool = createPool({
  host: process.env.MYSQL_HOST,
  port: Number(process.env.MYSQL_PORT ?? 3306),
  user: process.env.MYSQL_USER,
  password: process.env.MYSQL_PASSWORD,
  database: process.env.MYSQL_PREBETTER_DB,
})

const [legacy] = await pool.query<LegacyUser[] & any>('SELECT * FROM users')

let migrated = 0
let skipped = 0

for (const u of legacy as LegacyUser[]) {
  const [existing] = await pool.query<any[]>('SELECT id FROM `user` WHERE id = ?', [u.id])
  if ((existing as any[]).length > 0) {
    skipped++
    continue
  }

  const now = new Date()
  const createdAt = u.created_at ?? now
  const updatedAt = u.updated_at ?? now
  const role = u.is_superuser ? 'admin' : 'user'
  const name = u.full_name ?? u.username

  const conn = await pool.getConnection()
  try {
    await conn.beginTransaction()

    await conn.query(
      'INSERT INTO `user` (id, name, email, emailVerified, username, displayUsername, role, banned, createdAt, updatedAt) ' +
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
      [u.id, name, u.email, 1, u.username, u.username, role, 0, createdAt, updatedAt],
    )

    await conn.query(
      'INSERT INTO `account` (id, accountId, providerId, userId, password, createdAt, updatedAt) ' +
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
      [randomUUID(), u.id, 'credential', u.id, u.hashed_password, createdAt, updatedAt],
    )

    await conn.commit()
    migrated++
  } catch (err) {
    await conn.rollback()
    throw err
  } finally {
    conn.release()
  }
}

console.log(`migrated=${migrated} skipped=${skipped} total=${(legacy as LegacyUser[]).length}`)
await pool.end()
