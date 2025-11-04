import tailwindcss from "@tailwindcss/vite";

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',
  devtools: { enabled: true },
  modules: [
    '@nuxt/icon',
    'shadcn-nuxt',
    '@vueuse/nuxt',
    '@nuxtjs/color-mode',
    '@nuxtjs/seo',
    'nuxt-auth-utils',
  ],
  runtimeConfig: {
    apiBase: process.env.API_BASE_URL || 'http://localhost:8000',
    session: {
      maxAge: 8 * 60 * 60, // 8 hours
      password: process.env.NUXT_SESSION_PASSWORD || '',
      cookie: {
        secure: process.env.NODE_ENV === 'production' && !process.env.DISABLE_SECURE_COOKIES,
        httpOnly: true,
        sameSite: 'lax'
      }
    },
  },
  // Basic SEO site configuration
  site: {
    name: 'Prebetter IDS Dashboard',
    description: 'A modern Intrusion Detection System dashboard for Prelude IDS',
    defaultLocale: 'de',
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
  vite: {
    plugins: [
      tailwindcss(),
    ],
  },
})
