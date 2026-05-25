import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// Build target switch:
//   - VITE_BUILD_TARGET=web        → base "/"   (default; SPA on a domain root)
//   - VITE_BUILD_TARGET=tauri      → base "./"  (Tauri Desktop, file:// protocol)
//   - VITE_BUILD_TARGET=capacitor  → base "./"  (Capacitor Android, file:// protocol)
//
// Tauri/Capacitor load index.html via file://, so all asset URLs MUST be relative.
const buildTarget = process.env.VITE_BUILD_TARGET ?? 'web'
const base = buildTarget === 'web' ? '/' : './'

export default defineConfig({
  base,
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 3000,
    strictPort: false,
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
    },
  },
  build: {
    target: 'es2022',
    sourcemap: false,
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-vue': ['vue', 'vue-router', 'pinia'],
          'vendor-naive': ['naive-ui'],
          'vendor-charts': ['echarts', 'd3', '@antv/g6'],
        },
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['src/**/__tests__/**/*.spec.ts'],
  },
})
