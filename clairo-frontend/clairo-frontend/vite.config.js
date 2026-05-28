import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Optional proxy — uncomment if you hit CORS issues:
    // proxy: {
    //   '/upload': 'http://localhost:8000',
    //   '/appeal': 'http://localhost:8000',
    //   '/risk':   'http://localhost:8000',
    //   '/rag':    'http://localhost:8000',
    //   '/export': 'http://localhost:8000',
    //   '/analytics': 'http://localhost:8000',
    // }
  }
})
