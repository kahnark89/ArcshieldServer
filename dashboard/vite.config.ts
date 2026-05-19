import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/dashboard/',
  build: {
    outDir: 'dist',
  },
  server: {
    proxy: {
      '/events': 'http://localhost:8000',
      '/twin': 'http://localhost:8000',
      '/config': 'http://localhost:8000',
      '/media': 'http://localhost:8000',
    },
  },
})
