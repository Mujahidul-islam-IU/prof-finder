import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  // Ensure /admin route is handled by the SPA (index.html)
  appType: 'spa',
  // Expose env variables starting with VITE_ to the frontend
  define: {
    // Fallback: empty string means use relative URLs (for Vite proxy in dev)
  },
})
