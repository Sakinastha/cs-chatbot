// vite.config.js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        // 🔧 Removed the rewrite rule to preserve `/api/...` path
      },
      '/chat': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/reset-history': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/chat-history': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/curriculum': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      }
    },
  },
})
