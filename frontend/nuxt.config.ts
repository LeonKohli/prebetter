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
  future: {
    compatibilityVersion: 4,
  },
  runtimeConfig: {
    // Private key, only available on the server
    apiBase: process.env.API_BASE_URL || 'http://localhost:8000',
    public: {
      // Public keys, available on client
    },
  },
  // Basic SEO site configuration
  site: {
    name: 'Prebetter SIEM Dashboard',
    description: 'A modern Security Information and Event Management dashboard for Prelude IDS',
    defaultLocale: 'en',
  },
  css: ['~/assets/css/main.css'],
  shadcn: {
    prefix: '',
    componentDir: './app/components/ui'
  },
  colorMode: {
    classSuffix: ''
  },
  vite: {
    plugins: [
      tailwindcss(),
    ],
  },
})