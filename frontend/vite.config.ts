import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [
    vue(),
    ...(mode === 'development' ? [vueDevTools()] : []),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  build: {
    // CSP's img-src is 'self' only (no data:) — disable Vite's default
    // sub-4KB asset inlining so a future small image reference can't get
    // silently base64-inlined into a data: URI and blocked by the CSP.
    assetsInlineLimit: 0,
  },
  server: {
    headers: {
      'Content-Security-Policy': [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self'",
        "connect-src 'self' ws:",
        "font-src 'self'",
        "frame-src 'none'",
        "object-src 'none'",
      ].join('; '),
    },
  },
}))
