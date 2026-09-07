import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'node',
    dir: fileURLToPath(new URL('.', import.meta.url)),
    include: ['**/*.test.ts'],
    testTimeout: 15000,
    hookTimeout: 120000,
  },
})
