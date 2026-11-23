import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',
  // Keep the Nuxt 3 folder layout (pages/, components/ ... at the project root).
  // Needed if you scaffolded with a newer Nuxt that defaults to an app/ folder.
  srcDir: '.',
  devtools: { enabled: false },

  experimental: {
  appManifest: false,
  },
  
  ssr: false, // single-page app: simpler for a student project, no server-side cookie issues
  modules: ['shadcn-nuxt'],
  css: ['~/assets/css/tailwind.css'],
  vite: {
    plugins: [tailwindcss()],
  },
 shadcn: {
  prefix: '',
  componentDir: './components/ui',
},
  runtimeConfig: {
    public: {
      // Overridden by NUXT_PUBLIC_* variables in frontend/.env
      apiBase: 'http://localhost:8000',
      recaptchaSiteKey: '',
    },
  },
  app: {
    head: {
      title: 'Student Gig & Skill Marketplace',
      meta: [{ name: 'viewport', content: 'width=device-width, initial-scale=1' }],
    },
  },
})