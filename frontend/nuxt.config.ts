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
    'nuxt-auth-utils',
    '@nuxt/fonts',
  ],
  runtimeConfig: {
    // Empty defaults - overridden by NUXT_* env vars at runtime (12-factor)
    // NUXT_API_BASE, NUXT_SESSION_PASSWORD, etc.
    apiBase: '',
    session: {
      maxAge: 604800, // 7 days - must match REFRESH_TOKEN_EXPIRE_DAYS
      password: '',
      cookie: {
        secure: true,
        httpOnly: true,
        sameSite: 'lax',
      },
    },
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
      tailwindcss() as any,
    ],
  },
})
