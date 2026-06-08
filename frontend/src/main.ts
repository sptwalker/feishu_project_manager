import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

import App from './App.vue'
import router from './router'
import './styles/main.css'
import { useBrandingStore } from './stores/branding'

const app = createApp(App)

// 注册所有 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

const pinia = createPinia()
app.use(pinia)
app.use(router)
app.use(ElementPlus, { locale: zhCn })

// 启动前拉取并应用本实例品牌配置（logo / 标题 / 主题色），mount 前应用避免首屏闪烁；
// 接口故障时带 800ms 超时回退内置默认值，不阻断启动。
;(async () => {
  const branding = useBrandingStore(pinia)
  await branding.fetchBranding()
  branding.applyBranding()
  app.mount('#app')
})()
