import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

const nativeModes = new Set(['tauri', 'capacitor'])

export default defineConfig(({ mode }) => {
  const buildTarget = process.env.VITE_BUILD_TARGET ?? (nativeModes.has(mode) ? mode : 'web')
  const base = buildTarget === 'web' ? '/' : './'

  return {
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
            if (
              id.includes('node_modules/vue') ||
              id.includes('node_modules/pinia') ||
              id.includes('node_modules/vue-router')
            ) {
              return 'vendor-vue'
            }
            if (id.includes('node_modules/naive-ui')) {
              return 'vendor-naive'
            }
            if (id.includes('node_modules/echarts')) {
              return 'vendor-echarts'
            }
            if (id.includes('node_modules/d3')) {
              return 'vendor-d3'
            }
            if (id.includes('node_modules/@antv/g6')) {
              return 'vendor-g6'
            }
            if (id.includes('node_modules/axios')) {
              return 'vendor-axios'
            }
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
  }
})
