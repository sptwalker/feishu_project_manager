import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// 后端代理目标：默认 8000，可用 VITE_PROXY_TARGET 覆盖（用于连测试实例）
const proxyTarget = process.env.VITE_PROXY_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: proxyTarget,
        changeOrigin: true
      }
    }
  }
})
