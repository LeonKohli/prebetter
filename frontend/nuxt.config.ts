// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2024-04-03',
  devtools: { enabled: true },

  future: {
    compatibilityVersion: 4,
  },

  runtimeConfig: {
    public: {
      apiBase: 'http://127.0.0.1:8000'
    }
  },

  modules: [
    'nuxt-auth-utils',
    '@nuxt/icon',
    '@nuxtjs/tailwindcss',
    'shadcn-nuxt',
    '@nuxtjs/color-mode',
  ],
  colorMode: {
    classPrefix: '',
    classSuffix: ''
  },

  shadcn: {
    prefix: '',
    componentDir: './app/components/ui'
  },

  typescript: {
    strict: false
  },
})