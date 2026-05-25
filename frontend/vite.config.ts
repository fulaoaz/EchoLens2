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
        manualChunks(id) {
          // Vue 核心
          if (id.includes('node_modules/vue') || id.includes('node_modules/pinia') || id.includes('node_modules/vue-router')) {
            return 'vendor-vue'
          }
          // Naive UI
          if (id.includes('node_modules/naive-ui')) {
            return 'vendor-naive'
          }
          // 图表库
          if (id.includes('node_modules/echarts')) {
            return 'vendor-echarts'
          }
          if (id.includes('node_modules/d3')) {
            return 'vendor-d3'
          }
          if (id.includes('node_modules/@antv/g6')) {
            return 'vendor-g6'
          }
          // Axios
          if (id.includes('node_modules/axios')) {
            return 'vendor-axios'
          }
          // 其他 node_modules
          if (id.includes('node_modules')) {
            return 'vendor-misc'
          }
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
