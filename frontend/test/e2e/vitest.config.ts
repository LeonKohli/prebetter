import { fileURLToPath } from 'node:url'
import { defineVitestConfig } from '@nuxt/test-utils/config'

export default defineVitestConfig({
  test: {
    environment: 'nuxt',
    dir: fileURLToPath(new URL('.', import.meta.url)),
    include: ['**/*.test.ts'],
    environmentOptions: {
      nuxt: {
        rootDir: fileURLToPath(new URL('../..', import.meta.url)),
        mock: {
          intersectionObserver: true,
          indexedDb: true,
        },
      },
    },
  },
})
