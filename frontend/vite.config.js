import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  base: process.env.NODE_ENV === 'production' ? process.env.VITE_EDTRACE_BASE_DIR : '/',
  build: { outDir: process.env.VITE_EDTRACE_DIST_DIR },
  plugins: [react()],
})
