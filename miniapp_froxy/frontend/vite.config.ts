import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    proxy: { '/api': 'http://127.0.0.1:5055', '/assets': 'http://127.0.0.1:5055' }
  },
  build: {
    outDir: '../dist',
    emptyOutDir: true,
    sourcemap: false,
    target: 'es2020'
  }
})
