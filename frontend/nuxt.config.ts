import tailwindcss from "@tailwindcss/vite";

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-12-05',
  devtools: { enabled: true },
  modules: [
    '@nuxt/icon',
    'shadcn-nuxt',
    '@vueuse/nuxt',
    '@nuxtjs/color-mode',
    '@nuxt/fonts',
  ],
  runtimeConfig: {
    // Empty default - overridden by NUXT_API_BASE at runtime (12-factor).
    // Better Auth reads its own env (BETTER_AUTH_*, MYSQL_*) in server/utils/auth.ts.
    apiBase: '',
  },
  css: ['~/assets/css/tailwind.css'],
  shadcn: {
    prefix: '',
    componentDir: './app/components/ui'
  },
  colorMode: {
    classSuffix: '',
    preference: 'system', // Default to auto (respects OS theme)
    fallback: 'light'    // Fallback if system preference can't be detected
  },
  fonts: {
    families: [
      // Display font for headings and emphasis
      {
        name: 'Space Grotesk',
        provider: 'google',
        weights: [500, 600, 700],
        subsets: ['latin'],
        display: 'swap'
      },
      // Body font for UI and general content
      {
        name: 'Inter',
        provider: 'google',
        weights: [400, 500, 600, 700],
        subsets: ['latin'],
        display: 'swap'
      },
      // Monospace font for data, IPs, hashes, timestamps
      {
        name: 'Geist Mono',
        provider: 'google',
        weights: [400, 500, 600],
        subsets: ['latin'],
        display: 'swap'
      },
    ],
  },
  vite: {
    plugins: [
      tailwindcss(),
    ],
  },
})
