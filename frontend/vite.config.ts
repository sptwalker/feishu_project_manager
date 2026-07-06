import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import { execSync } from 'child_process'

// 后端代理目标：默认 8000，可用 VITE_PROXY_TARGET 覆盖（用于连测试实例）
const proxyTarget = process.env.VITE_PROXY_TARGET || 'http://localhost:8000'

// 部署版本标记（侧栏底部展示，用于确认线上构建是否为最新）。
// 优先用构建参数 VITE_APP_VERSION（Docker 里传 git 短哈希）；本地退回读取 git；都拿不到用 'dev'。
function gitHash(): string {
  try { return execSync('git rev-parse --short HEAD').toString().trim() } catch { return '' }
}
const appVersion = process.env.VITE_APP_VERSION || gitHash() || 'dev'
const buildTime = new Date().toISOString().slice(0, 16).replace('T', ' ') + ' UTC'

export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(appVersion),
    __BUILD_TIME__: JSON.stringify(buildTime),
  },
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
