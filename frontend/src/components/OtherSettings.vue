<template>
  <div class="other-settings" v-loading="loading">
    <section class="card">
      <h3 class="card-title">周例会次数设置</h3>

      <template v-if="state">
        <!-- 本周已召开 -->
        <div v-if="state.this_week_recorded" class="info-block">
          <div class="info-row">
            <span class="ilabel">本周状态</span>
            <span class="ival ok">本周已召开第 {{ state.this_week_count }} 次周例会</span>
          </div>
          <div class="info-row">
            <span class="ilabel">下一次周例会</span>
            <span class="ival">{{ state.calibration_monday }}（周一）· 应为第 <b>{{ state.calibration_count }}</b> 次</span>
          </div>
        </div>

        <!-- 本周未召开 -->
        <div v-else class="info-block">
          <div class="info-row">
            <span class="ilabel">上一次周例会</span>
            <span class="ival">
              <template v-if="state.last_meeting">{{ state.last_meeting.date }} · 第 {{ state.last_meeting.count }} 次</template>
              <span v-else class="muted">暂无记录</span>
            </span>
          </div>
          <div class="info-row">
            <span class="ilabel">本周周例会</span>
            <span class="ival">{{ state.this_week_monday }}（周一）· 将为第 <b>{{ state.calibration_count }}</b> 次</span>
          </div>
        </div>

        <!-- 校准 -->
        <div class="calibrate">
          <span class="ilabel">校准次数</span>
          <el-input-number
            v-model="editCount" :min="1" :disabled="!isAdmin" controls-position="right" style="width: 140px"
          />
          <el-button type="primary" :loading="saving" :disabled="!isAdmin || editCount === state.calibration_count" @click="save">
            保存
          </el-button>
          <span v-if="!isAdmin" class="muted hint">（仅管理员可修改）</span>
        </div>
        <p class="tip muted">
          说明：周会次数按自然周递增——同一周内次数不变，跨到新的一周自动 +1。
          修改"校准次数"将把 {{ state.calibration_monday }} 那一周设为该次数，并以此为基准向后推算。
        </p>
      </template>
    </section>

    <section class="card">
      <h3 class="card-title">项目进展催办设置</h3>
      <p class="tip muted" style="margin-top:0">
        飞书机器人每天定时扫描项目进展，对「进展停滞」或「存在未闭合待办」的项目在群里催办相关负责人。
        下方设置进展停滞的天数阈值——最新进展距今超过该天数的项目将被催办。
      </p>
      <div class="calibrate" style="border-top:none; padding-top:0">
        <span class="ilabel">停滞天数</span>
        <el-input-number
          v-model="stallDays" :min="1" :max="365" :disabled="!isAdmin" controls-position="right" style="width: 140px"
        />
        <el-button type="primary" :loading="savingStall" :disabled="!isAdmin || stallDays === savedStallDays" @click="saveStallDays">
          保存
        </el-button>
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
import { useMeetingStore } from '@/stores/meeting'
import { useAuthStore } from '@/stores/auth'
import { settingsApi } from '@/api/resources'

const meeting = useMeetingStore()
const auth = useAuthStore()

const loading = ref(false)
const saving = ref(false)
const editCount = ref(0)

const state = computed(() => meeting.state)
const isAdmin = computed(() => auth.currentUser?.role === 'admin')

/* 项目进展催办：停滞天数阈值 */
const stallDays = ref(30)
const savedStallDays = ref(30)
const savingStall = ref(false)

async function loadStallDays() {
  try {
    const r = await settingsApi.getFollowupStallDays()
    stallDays.value = r.days
    savedStallDays.value = r.days
  } catch {
    // 读取失败保持默认值
  }
}

async function saveStallDays() {
  savingStall.value = true
  try {
    const r = await settingsApi.setFollowupStallDays(stallDays.value)
    stallDays.value = r.days
    savedStallDays.value = r.days
    ElMessage.success('催办天数已保存')
  } catch {
    ElMessage.error('保存失败（需要管理员权限）')
  } finally {
    savingStall.value = false
  }
}

async function load() {
  loading.value = true
  try {
    await meeting.load()
    editCount.value = meeting.state?.calibration_count ?? 0
  } finally {
    loading.value = false
  }
  await loadStallDays()
}

async function save() {
  saving.value = true
  try {
    await meeting.setCount(editCount.value)
    editCount.value = meeting.state?.calibration_count ?? editCount.value
    ElMessage.success('周会次数已校准')
  } catch {
    ElMessage.error('保存失败（需要管理员权限）')
  } finally {
    saving.value = false
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
    await load()
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail ? `导入失败：${detail}` : '导入失败（需要管理员权限或文件格式错误）')
  } finally {
    importing.value = false
  }
}

onMounted(load)
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

.info-block { display: flex; flex-direction: column; gap: var(--sp-3); margin-bottom: var(--sp-4); }
.info-row { display: flex; align-items: center; gap: var(--sp-3); }
.ilabel { width: 96px; flex-shrink: 0; color: var(--c-ink-3); font-size: 13px; }
.ival { color: var(--c-ink); font-weight: 500; }
.ival.ok { color: #1a73e8; font-weight: 600; }

.calibrate { display: flex; align-items: center; gap: var(--sp-3); padding-top: var(--sp-3); border-top: 1px solid var(--c-border); }
.hint { font-size: 12px; }
.tip { margin: var(--sp-3) 0 0; font-size: 12px; line-height: 1.6; }
</style>
