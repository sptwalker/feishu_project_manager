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

        <!-- 校准（周会进行中时禁用，避免改动正在记录的周会次数导致进展标签错位） -->
        <div class="calibrate">
          <span class="ilabel">校准次数</span>
          <el-input-number
            v-model="editCount" :min="1" :disabled="!isAdmin || state.active" controls-position="right" style="width: 140px"
          />
          <el-button type="primary" :loading="saving" :disabled="!isAdmin || state.active || editCount === state.calibration_count" @click="save">
            保存
          </el-button>
          <span v-if="!isAdmin" class="muted hint">（仅管理员可修改）</span>
          <span v-else-if="state.active" class="muted hint">（周会进行中，结束后可校准）</span>
        </div>
        <p class="tip muted">
          说明：周会周期按"上次会议日期 + {{ state.new_cycle_days ?? 3 }} 天"递进——上轮周会结束满 {{ state.new_cycle_days ?? 3 }} 天后即可开启新一轮周会周期。
          修改"校准次数"将把下次开启的周会设为该次数。
        </p>
      </template>
    </section>

    <!-- 周会自动开启：每周四自动开周会的运行时开关（改后立即生效，无需重启/改配置） -->
    <section class="card">
      <h3 class="card-title">周会自动开启</h3>
      <p class="tip muted" style="margin-top:0">
        开启后，每周四（工作日）14:00 若周会未开启，系统将自动开启新一轮周会并通知核心群。
        自动催更开启后，每周五、周日 14:00 在核心群发进展更新催办（仅周会进行中时发送）。
      </p>
      <div class="calibrate" style="border-top:none; padding-top:0">
        <span class="ilabel">自动开启</span>
        <el-switch v-model="autoOpen" :disabled="!isAdmin || savingAutoOpen" @change="saveAutoOpen" />
        <span class="muted hint">{{ autoOpen ? '已开启（每周四自动）' : '已关闭（仅手动开启）' }}</span>
        <span v-if="!isAdmin" class="muted hint">（仅管理员可修改）</span>
      </div>
      <div class="calibrate" style="border-top:none; padding-top:var(--sp-2)">
        <span class="ilabel">自动催更</span>
        <el-switch v-model="autoReminder" :disabled="!isAdmin || savingAutoReminder" @change="saveAutoReminder" />
        <span class="muted hint">{{ autoReminder ? '已开启（每周五、周日自动催更）' : '已关闭' }}</span>
      </div>
      <!-- 【临时测试】点击后约3分钟执行一次催更，用于验证催更链路；验证完删除本段 -->
      <div class="calibrate" style="border-top:1px dashed var(--c-border); padding-top:var(--sp-2)">
        <span class="ilabel">测试催更</span>
        <el-button size="small" type="warning" plain :loading="testingReminder" :disabled="!isAdmin" @click="doTestReminder">
          立即测试（3分钟后执行一次）
        </el-button>
        <span class="muted hint">临时测试按钮，用于排查催更是否能正常发出</span>
      </div>
      <!-- 【临时测试】催更诊断：一键获取完整诊断报告，复制后发给开发；验证完删除本段 -->
      <div class="calibrate" style="border-top:none; padding-top:var(--sp-2); align-items:flex-start; flex-wrap:wrap">
        <span class="ilabel">催更诊断</span>
        <div style="flex:1; min-width:280px">
          <div style="display:flex; gap:var(--sp-2); align-items:center; flex-wrap:wrap">
            <el-button size="small" type="primary" plain :loading="loadingDiag" :disabled="!isAdmin" @click="getDiag">
              获取诊断信息
            </el-button>
            <el-button size="small" :disabled="!diagReport" @click="copyDiag">复制</el-button>
            <span class="muted hint">先点「测试催更」，约3分钟后再点这里获取结果，复制发给开发</span>
          </div>
          <el-input
            v-if="diagReport" v-model="diagReport" type="textarea" :rows="16" readonly
            style="margin-top:8px" input-style="font-family:monospace;font-size:12px;white-space:pre"
          />
        </div>
      </div>
    </section>

    <!-- 飞书核心群 chat_id：周会纪要文档链接分享的目标群（所见即所得，留空不发送） -->
    <section class="card">
      <h3 class="card-title">飞书核心群 chat_id</h3>
      <p class="tip muted" style="margin-top:0">
        周会纪要生成后会把飞书文档链接分享到此核心群。留空则不发送。
      </p>
      <div class="calibrate" style="border-top:none; padding-top:0">
        <span class="ilabel">chat_id</span>
        <el-input
          v-model="coreChatId" :disabled="!isAdmin" placeholder="oc_ 开头，留空则不发送" style="width: 280px" clearable
        />
        <el-button type="primary" :loading="savingChatId" :disabled="!isAdmin || coreChatId === savedChatId" @click="saveCoreChatId">
          保存
        </el-button>
        <span v-if="!isAdmin" class="muted hint">（仅管理员可修改）</span>
      </div>
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

/* 飞书核心群 chat_id：周会纪要文档链接分享的目标群 */
const coreChatId = ref('')
const savedChatId = ref('')
const savingChatId = ref(false)

async function loadCoreChatId() {
  try {
    const r = await settingsApi.getCoreGroupChatId()
    coreChatId.value = r.chat_id
    savedChatId.value = r.chat_id
  } catch {
    // 读取失败保持空值
  }
}

async function saveCoreChatId() {
  savingChatId.value = true
  try {
    const r = await settingsApi.setCoreGroupChatId(coreChatId.value.trim())
    coreChatId.value = r.chat_id
    savedChatId.value = r.chat_id
    ElMessage.success('核心群 chat_id 已保存')
  } catch {
    ElMessage.error('保存失败（需要管理员权限）')
  } finally {
    savingChatId.value = false
  }
}

/* 周会自动开启：每周四自动开周会的运行时开关 */
const autoOpen = ref(false)
const savingAutoOpen = ref(false)

async function loadAutoOpen() {
  try {
    const r = await settingsApi.getAutoOpenMeeting()
    autoOpen.value = r.enabled
  } catch {
    // 读取失败保持关闭
  }
}

async function saveAutoOpen(val: boolean) {
  savingAutoOpen.value = true
  try {
    const r = await settingsApi.setAutoOpenMeeting(val)
    autoOpen.value = r.enabled
    ElMessage.success(r.enabled ? '已开启周会自动开启' : '已关闭周会自动开启')
  } catch {
    autoOpen.value = !val  // 失败回滚开关状态
    ElMessage.error('保存失败（需要管理员权限）')
  } finally {
    savingAutoOpen.value = false
  }
}

/* 周会自动催更：每周五/周日自动在核心群催更的运行时开关 */
const autoReminder = ref(false)
const savingAutoReminder = ref(false)

async function loadAutoReminder() {
  try {
    const r = await settingsApi.getAutoReminder()
    autoReminder.value = r.enabled
  } catch {
    // 读取失败保持关闭
  }
}

async function saveAutoReminder(val: boolean) {
  savingAutoReminder.value = true
  try {
    const r = await settingsApi.setAutoReminder(val)
    autoReminder.value = r.enabled
    ElMessage.success(r.enabled ? '已开启周会自动催更' : '已关闭周会自动催更')
  } catch {
    autoReminder.value = !val  // 失败回滚开关状态
    ElMessage.error('保存失败（需要管理员权限）')
  } finally {
    savingAutoReminder.value = false
  }
}

/* 【临时测试】点击后安排约3分钟后的一次性催更，并弹窗展示当前4个守卫状态便于诊断；验证后删除 */
const testingReminder = ref(false)
async function doTestReminder() {
  testingReminder.value = true
  try {
    const r = await settingsApi.testReminder()
    const g = r.guards
    const mark = (b: boolean) => (b ? '✓' : '✗')
    await ElMessageBox.alert(
      `已安排，将于约 ${r.run_at}（北京时间）执行一次催更。\n\n` +
      `当前催更守卫状态（任一为 ✗ 都会导致不发送）：\n` +
      `${mark(g.auto_reminder_enabled)} 催更开关已开\n` +
      `${mark(g.active_meeting)} 存在进行中的周会${g.active_meeting ? '' : '（无 → 催更会跳过）'}\n` +
      `${mark(g.core_chat_id_configured)} 核心群 chat_id 已配置\n` +
      `${mark(g.feishu_notify_enabled)} 飞书通知总开关已开\n\n` +
      `请于约3分钟后留意核心群消息与后端日志。`,
      '测试催更已安排',
      { type: 'info', confirmButtonText: '知道了', dangerouslyUseHTMLString: false },
    )
  } catch {
    ElMessage.error('安排失败（需管理员；且后端调度器需已启动 AUTO_OPEN_MEETING_ENABLED/SCHEDULER_ENABLED）')
  } finally {
    testingReminder.value = false
  }
}

/* 【临时测试】获取催更链路诊断报告文本，展示到文本框供复制；验证后删除 */
const loadingDiag = ref(false)
const diagReport = ref('')
async function getDiag() {
  loadingDiag.value = true
  try {
    const r = await settingsApi.getDiagnostics()
    diagReport.value = r.report
  } catch {
    ElMessage.error('获取诊断失败（需要管理员权限）')
  } finally {
    loadingDiag.value = false
  }
}
async function copyDiag() {
  try {
    await navigator.clipboard.writeText(diagReport.value)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.info('复制失败，请在文本框内手动全选复制')
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
  await loadCoreChatId()
  await loadAutoOpen()
  await loadAutoReminder()
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
