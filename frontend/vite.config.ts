import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The single-command launcher supplies the Django port. Browser requests
// remain same-origin (/api/*); Django is never directly exposed to the VPN.
const apiTarget = process.env.SIREIKON_API_PORT
  ? `http://127.0.0.1:${Number(process.env.SIREIKON_API_PORT)}`
  : 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
      '/v1': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})
