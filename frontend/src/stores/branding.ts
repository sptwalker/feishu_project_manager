import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import defaultLogo from '@/assets/logo.png'

/* 品牌/表现差异化配置（与后端 /api/v1/branding 对应） */
export interface Branding {
  brand_sidebar: string
  brand_login: string
  brand_mark: string
  page_title: string
  login_headline: string
  login_sub: string
  org_scope: string
  dept_unit: string
  logo_url: string
  favicon_url: string
  theme: Record<string, string>
  sales_code_enabled: boolean
}

/* 内置默认值：接口失败或字段缺失时回退（与后端 config.py 默认一致） */
const DEFAULTS: Branding = {
  brand_sidebar: '<span class="brand-accent">P</span>roject <span class="brand-accent">M</span>anager',
  brand_login: '飞书<span class="accent">PM</span>',
  brand_mark: '飞',
  page_title: '飞书项目管理系统',
  login_headline: '把中长期项目<br />管理得<span class="accent">轻盈</span>。',
  login_sub: '里程碑 · 任务 · 风险 · 飞书联动 —— 一处掌握全局。',
  org_scope: '全公司',
  dept_unit: '部门',
  logo_url: '',
  favicon_url: '',
  theme: {},
  sales_code_enabled: false,
}

export const useBrandingStore = defineStore('branding', () => {
  const data = ref<Branding>({ ...DEFAULTS })

  /* 侧边栏 logo：接口给了 URL 用之，否则用构建内置默认图 */
  const logoSrc = computed(() => data.value.logo_url || defaultLogo)

  /* 拉取本实例品牌配置（公开接口，无需 token）。带超时回退默认，避免接口故障导致白屏。 */
  async function fetchBranding() {
    try {
      const ctrl = new AbortController()
      const timer = setTimeout(() => ctrl.abort(), 800)
      const resp = await fetch('/api/v1/branding', { signal: ctrl.signal })
      clearTimeout(timer)
      if (resp.ok) {
        const json = await resp.json()
        data.value = { ...DEFAULTS, ...json }
      }
    } catch {
      // 失败保持默认值（产品默认品牌），不阻断启动
    }
  }

  /* 应用品牌：标签标题 + favicon + 主题色覆盖（在 mount 前调用，避免闪烁） */
  function applyBranding() {
    document.title = data.value.page_title
    if (data.value.favicon_url) {
      let link = document.querySelector<HTMLLinkElement>('link[rel="icon"]')
      if (!link) {
        link = document.createElement('link')
        link.rel = 'icon'
        document.head.appendChild(link)
      }
      link.href = data.value.favicon_url
    }
    // 主题色：覆盖 :root CSS 变量（仅接口返回的非空项；状态语义色不在其列，沿用默认）
    for (const [key, value] of Object.entries(data.value.theme || {})) {
      document.documentElement.style.setProperty(key, value)
    }
  }

  return { data, logoSrc, fetchBranding, applyBranding }
})
