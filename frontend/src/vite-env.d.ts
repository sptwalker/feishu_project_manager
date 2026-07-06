/// <reference types="vite/client" />

// 构建时注入（见 vite.config.ts define）：部署版本号与构建时间
declare const __APP_VERSION__: string
declare const __BUILD_TIME__: string

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<Record<string, never>, Record<string, never>, unknown>
  export default component
}
