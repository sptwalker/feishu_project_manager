<template>
  <div class="branding-settings" v-loading="loading">
    <section class="card">
      <h3 class="card-title">品牌设置</h3>
      <p class="tip muted" style="margin-top:0">
        配置本实例的 logo、名称、文案与主题色。保存后立即生效，无需登录服务器或重启。
        留空的项回退到服务器 .env 默认。仅管理员可修改。
      </p>

      <!-- Logo -->
      <div class="brow">
        <span class="blabel">Logo</span>
        <div class="logo-box">
          <img v-if="form.logo_url" :src="form.logo_url" class="logo-preview" alt="logo" />
          <span v-else class="muted hint">（未设置，用内置默认）</span>
        </div>
        <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/svg+xml,image/webp" style="display:none" @change="onLogoChosen" />
        <el-button size="small" :disabled="!isAdmin" @click="fileInput?.click()">上传图片</el-button>
        <el-button v-if="form.logo_url" size="small" text type="danger" :disabled="!isAdmin" @click="form.logo_url = ''">清除</el-button>
        <span class="muted hint">建议宽 ~440px、&lt;100KB</span>
      </div>

      <!-- 文字 -->
      <div class="brow"><span class="blabel">浏览器标题</span>
        <el-input v-model="form.page_title" :disabled="!isAdmin" placeholder="浏览器标签标题" style="width: 360px" /></div>
      <div class="brow"><span class="blabel">侧栏名</span>
        <el-input v-model="form.brand_sidebar" :disabled="!isAdmin" placeholder='支持 HTML，如 <span class="brand-accent">P</span>M' style="width: 360px" /></div>
      <div class="brow"><span class="blabel">首页范围词</span>
        <el-input v-model="form.org_scope" :disabled="!isAdmin" placeholder="全公司 / 营销销售部" style="width: 200px" />
        <span class="blabel2">单位词</span>
        <el-input v-model="form.dept_unit" :disabled="!isAdmin" placeholder="部门 / 团队" style="width: 140px" /></div>
      <div class="brow"><span class="blabel">登录页名</span>
        <el-input v-model="form.brand_login" :disabled="!isAdmin" placeholder='支持 HTML' style="width: 360px" /></div>
      <div class="brow"><span class="blabel">方块标记</span>
        <el-input v-model="form.brand_mark" :disabled="!isAdmin" placeholder="登录页左上方块字，如 飞 / 销" style="width: 140px" maxlength="4" /></div>
      <div class="brow"><span class="blabel">登录主标语</span>
        <el-input v-model="form.login_headline" :disabled="!isAdmin" type="textarea" :autosize="{minRows:1,maxRows:3}" placeholder="支持 HTML、<br /> 换行" style="width: 360px" /></div>
      <div class="brow"><span class="blabel">登录副标语</span>
        <el-input v-model="form.login_sub" :disabled="!isAdmin" placeholder="一句话副标语" style="width: 360px" /></div>

      <!-- 主题色 -->
      <div class="brow"><span class="blabel">主题色</span>
        <el-color-picker v-model="form.accent" :disabled="!isAdmin" />
        <span class="cmini">强调色</span>
        <el-color-picker v-model="form.accent_hover" :disabled="!isAdmin" />
        <span class="cmini">悬停</span>
        <el-color-picker v-model="form.accent_soft" :disabled="!isAdmin" />
        <span class="cmini">浅底</span>
      </div>
      <div class="brow"><span class="blabel">侧栏色</span>
        <el-color-picker v-model="form.sidebar_bg" :disabled="!isAdmin" />
        <span class="cmini">背景</span>
        <el-color-picker v-model="form.sidebar_hover" :disabled="!isAdmin" />
        <span class="cmini">悬停</span>
      </div>

      <div class="brow">
        <span class="blabel"></span>
        <el-button type="primary" :loading="saving" :disabled="!isAdmin" @click="save">保存并应用</el-button>
        <span v-if="!isAdmin" class="muted hint">（仅管理员可修改）</span>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useBrandingStore } from '@/stores/branding'
import { brandingApi, type BrandingFull } from '@/api/resources'

const auth = useAuthStore()
const branding = useBrandingStore()
const isAdmin = computed(() => auth.currentUser?.role === 'admin')

const loading = ref(false)
const saving = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const form = reactive<BrandingFull>({
  brand_sidebar: '', brand_login: '', brand_mark: '', page_title: '',
  login_headline: '', login_sub: '', org_scope: '', dept_unit: '',
  logo_url: '', favicon_url: '', accent: '', accent_hover: '', accent_soft: '',
  sidebar_bg: '', sidebar_hover: '',
})

async function load() {
  loading.value = true
  try {
    const cfg = await brandingApi.get()
    Object.assign(form, cfg)
  } catch {
    // 非管理员或接口故障：保持空表单
  } finally {
    loading.value = false
  }
}

function onLogoChosen(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (file.size > 200 * 1024) {
    ElMessage.warning('图片偏大（建议 <100KB，最大 200KB），请压缩后再上传')
    return
  }
  const reader = new FileReader()
  reader.onload = () => { form.logo_url = String(reader.result || '') }
  reader.onerror = () => ElMessage.error('读取图片失败')
  reader.readAsDataURL(file)  // 转 base64 data URI，随表单存入 DB
}

async function save() {
  saving.value = true
  try {
    const cfg = await brandingApi.update({ ...form })
    Object.assign(form, cfg)
    // 立即刷新并应用品牌（当前页签即时变更：标题/favicon/主题色）
    await branding.fetchBranding()
    branding.applyBranding()
    ElMessage.success('品牌已保存并应用（其他页面刷新后生效）')
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail ? `保存失败：${detail}` : '保存失败（需要管理员权限）')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.branding-settings { padding: var(--sp-2) 0; }
.card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  padding: var(--sp-5);
  max-width: 680px;
  box-shadow: var(--shadow-sm);
}
.card-title { font-size: 15px; margin-bottom: var(--sp-4); }
.brow { display: flex; align-items: center; gap: var(--sp-3); margin-bottom: var(--sp-3); flex-wrap: wrap; }
.blabel { width: 84px; flex-shrink: 0; color: var(--c-ink-3); font-size: 13px; }
.blabel2 { color: var(--c-ink-3); font-size: 13px; }
.cmini { color: var(--c-ink-3); font-size: 12px; margin-right: var(--sp-2); }
.hint { font-size: 12px; }
.tip { margin-bottom: var(--sp-4); font-size: 12px; line-height: 1.6; }
.logo-box {
  min-width: 120px; height: 48px; display: flex; align-items: center;
  padding: 0 var(--sp-2); border: 1px dashed var(--c-border); border-radius: var(--r-sm);
  background: var(--c-canvas);
}
.logo-preview { max-height: 40px; max-width: 200px; object-fit: contain; }
</style>
