import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Served by FastAPI's StaticFiles mount at /preview, so asset URLs must be rooted there.
// Dev server proxies /api to the uvicorn backend so `npm run dev` works standalone.
export default defineConfig({
  base: '/preview/',
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8001',
    },
  },
})
