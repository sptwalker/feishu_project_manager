<template>
  <div class="other-settings">
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
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Upload } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { settingsApi } from '@/api/resources'

const auth = useAuthStore()
const isAdmin = computed(() => auth.currentUser?.role === 'admin')

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
.hint { font-size: 12px; }
.tip { margin: var(--sp-3) 0 0; font-size: 12px; line-height: 1.6; }
</style>
