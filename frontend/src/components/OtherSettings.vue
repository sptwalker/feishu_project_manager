<template>
  <div class="other-settings">
    <!-- 飞书机器人应用：本实例独立的 App ID/Secret（DB 优先于 .env，实现各实例独立机器人） -->
    <section class="card">
      <h3 class="card-title">飞书机器人应用</h3>
      <p class="tip muted" style="margin-top:0">
        配置本实例使用的飞书自建应用凭证（登录、群通知、催办私聊均用此机器人）。在此配置优先于服务器 .env；
        留空则回退 .env 默认。各实例配各自的应用即可独立管理、互不冲突。
      </p>
      <div class="form-row">
        <span class="ilabel">App ID</span>
        <el-input v-model="feishuAppId" :disabled="!isAdmin" placeholder="cli_ 开头" style="width: 320px" clearable />
      </div>
      <div class="form-row">
        <span class="ilabel">App Secret</span>
        <el-input
          v-model="feishuSecret" :disabled="!isAdmin" type="password" show-password
          :placeholder="secretSet ? '已配置（留空则保持不变）' : '请输入 App Secret'" style="width: 320px"
        />
      </div>
      <div class="form-row">
        <span class="ilabel"></span>
        <el-button type="primary" :loading="savingFeishu" :disabled="!isAdmin" @click="saveFeishuApp">保存</el-button>
        <span v-if="secretSet" class="muted hint ok">✓ 已配置密钥</span>
        <span v-if="!isAdmin" class="muted hint">（仅管理员可修改）</span>
      </div>
    </section>

    <section class="card">
      <h3 class="card-title">数据备份</h3>
      <p class="tip muted" style="margin-top:0">
        导出当前全部数据为 JSON 快照文件，可复制到其他环境上传导入。导入为<b>全量替换</b>——会清空并覆盖目标环境的现有数据。
      </p>
      <div class="backup-actions">
        <el-button type="primary" :icon="Download" :loading="exporting" :disabled="!isAdmin" @click="doExport">
          导出数据
        </el-button>
        <el-button :icon="Upload" :loading="importing" :disabled="!isAdmin" @click="triggerImport">
          导入数据
        </el-button>
        <input ref="fileInput" type="file" accept=".json,application/json" style="display:none" @change="onFileChosen" />
        <span v-if="!isAdmin" class="muted hint">（仅管理员可操作）</span>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Upload } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { settingsApi } from '@/api/resources'

const auth = useAuthStore()
const isAdmin = computed(() => auth.currentUser?.role === 'admin')

/* 飞书机器人应用凭证 */
const feishuAppId = ref('')
const feishuSecret = ref('')
const secretSet = ref(false)
const savingFeishu = ref(false)

async function loadFeishuApp() {
  try {
    const r = await settingsApi.getFeishuApp()
    feishuAppId.value = r.app_id
    secretSet.value = r.secret_set
  } catch {
    // 读取失败（非管理员或接口故障）保持空
  }
}

async function saveFeishuApp() {
  savingFeishu.value = true
  try {
    const payload: { app_id: string; app_secret?: string } = { app_id: feishuAppId.value.trim() }
    if (feishuSecret.value.trim()) payload.app_secret = feishuSecret.value.trim()
    const r = await settingsApi.setFeishuApp(payload)
    feishuAppId.value = r.app_id
    secretSet.value = r.secret_set
    feishuSecret.value = ''  // 保存后清空输入框，不回显密钥
    ElMessage.success('飞书应用配置已保存')
  } catch {
    ElMessage.error('保存失败（需要管理员权限）')
  } finally {
    savingFeishu.value = false
  }
}

/* 数据备份：导出 / 导入 */
const exporting = ref(false)
const importing = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

async function doExport() {
  exporting.value = true
  try {
    const resp = await settingsApi.exportBackup()
    const dispo = (resp.headers['content-disposition'] as string) || ''
    const m = dispo.match(/filename="?([^"]+)"?/)
    const filename = m ? m[1] : `feishu_pm_backup_${Date.now()}.json`
    const url = URL.createObjectURL(resp.data as Blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('已导出数据快照')
  } catch {
    ElMessage.error('导出失败（需要管理员权限）')
  } finally {
    exporting.value = false
  }
}

function triggerImport() {
  fileInput.value?.click()
}

async function onFileChosen(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  try {
    await ElMessageBox.confirm(
      `确定用「${file.name}」全量替换当前数据？此操作将清空并覆盖现有全部数据，不可恢复。`,
      '导入确认',
      { type: 'warning', confirmButtonText: '确定导入', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  importing.value = true
  try {
    const res = await settingsApi.importBackup(file)
    const summary = Object.entries(res.counts).map(([k, v]) => `${k}:${v}`).join('，')
    ElMessage.success(`导入成功（${summary}）`)
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail ? `导入失败：${detail}` : '导入失败（需要管理员权限或文件格式错误）')
  } finally {
    importing.value = false
  }
}

onMounted(loadFeishuApp)
</script>

<style scoped>
.other-settings { padding: var(--sp-2) 0; }
.card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  padding: var(--sp-5);
  max-width: 640px;
  margin-bottom: var(--sp-4);
  box-shadow: var(--shadow-sm);
}
.card-title { font-size: 15px; margin-bottom: var(--sp-4); }
.backup-actions { display: flex; align-items: center; gap: var(--sp-3); }
.form-row { display: flex; align-items: center; gap: var(--sp-3); margin-bottom: var(--sp-3); }
.form-row:last-child { margin-bottom: 0; }
.ilabel { width: 80px; flex-shrink: 0; color: var(--c-ink-3); font-size: 13px; }
.hint { font-size: 12px; }
.hint.ok { color: #3DBE7B; }
.tip { margin: var(--sp-3) 0 0; font-size: 12px; line-height: 1.6; }
</style>
