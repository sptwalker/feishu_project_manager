<template>
  <div class="meeting-settings" v-loading="loading">
    <section class="card">
      <h3 class="card-title">周例会次数设置</h3>

      <template v-if="state">
        <div v-if="state.this_week_recorded" class="info-block">
          <div class="info-row">
            <span class="ilabel">本周状态</span>
            <span class="ival ok">正在记录第 {{ state.this_week_count }} 次周例会</span>
          </div>
          <div class="info-row">
            <span class="ilabel">下一次周例会</span>
            <span class="ival muted">本次结束、满 {{ state.new_cycle_days ?? 3 }} 天后可开启下一轮</span>
          </div>
        </div>

        <div v-else class="info-block">
          <div class="info-row">
            <span class="ilabel">上一次周例会</span>
            <span class="ival">
              <template v-if="state.last_meeting && state.last_meeting.date">{{ state.last_meeting.date }} · 第 {{ state.last_meeting.count }} 次</template>
              <span v-else class="muted">暂无记录</span>
            </span>
          </div>
          <div class="info-row">
            <span class="ilabel">下一次周例会</span>
            <span class="ival">
              将为第 <b>{{ state.calibration_count }}</b> 次 ·
              <template v-if="state.can_open_new_cycle">现在即可开启新一轮</template>
              <template v-else>最早 {{ nextEarliestDate }} 可开启（上次结束满 {{ state.new_cycle_days ?? 3 }} 天）</template>
            </span>
          </div>
        </div>

        <div class="calibrate">
          <span class="ilabel">校准次数</span>
          <el-input-number
            v-model="editCount" :min="1" :disabled="!isAdmin || state.this_week_recorded" controls-position="right" style="width: 140px"
          />
          <el-button type="primary" :loading="saving" :disabled="!isAdmin || state.this_week_recorded || editCount === state.this_week_count" @click="save">
            保存
          </el-button>
          <span v-if="!isAdmin" class="muted hint">（仅管理员可修改）</span>
          <span v-else-if="state.this_week_recorded" class="muted hint">（周会进行中，结束后可校准）</span>
        </div>
        <p class="tip muted">
          说明：周会周期按"上次周会结束日期 + {{ state.new_cycle_days ?? 3 }} 天"递进——上轮周会结束满 {{ state.new_cycle_days ?? 3 }} 天后即可开启新一轮周会周期。
          "校准次数"用于纠正<b>当前（最近一次）周会的次数</b>；下一次周会据此递推。
        </p>
      </template>
    </section>

    <section class="card">
      <h3 class="card-title">周会自动开启</h3>
      <p class="tip muted" style="margin-top:0">
        开启后，每周四（工作日）14:00 若周会未开启，系统将自动开启新一轮周会并通知周会群。
        自动催更开启后，每周五、周日 14:00 在周会群发进展更新催办（仅周会进行中时发送）。
      </p>
      <div class="calibrate" style="border-top:none; padding-top:0">
        <span class="ilabel">自动开启</span>
        <el-switch v-model="autoOpen" :disabled="!isAdmin || savingAutoOpen" @change="saveAutoOpen" />
        <span class="muted hint">{{ autoOpen ? '已开启（每周四自动）' : '已关闭（仅手动开启）' }}</span>
        <span v-if="!isAdmin" class="muted hint">（仅管理员可修改）</span>
      </div>
      <div class="calibrate" style="border-top:none; padding-top:var(--sp-2)">
        <span class="ilabel">自动催更</span>
        <el-switch v-model="autoReminder" :disabled="!isAdmin || savingAutoReminder || !autoOpen" @change="saveAutoReminder" />
        <span class="muted hint">{{ autoReminder ? '已开启（每周五、周日自动催更）' : '已关闭' }}</span>
        <span v-if="!autoOpen" class="muted hint">（需先开启「自动开启」）</span>
      </div>
    </section>

    <section class="card">
      <h3 class="card-title">飞书周会群 chat_id</h3>
      <p class="tip muted" style="margin-top:0">
        周会纪要生成后会把飞书文档链接分享到此周会群；周会自动开启/催更通知也发送到此群。留空则不发送。
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
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

/* 下一轮最早可开启日期 = 上次周会日期 + 周期天数（本地时区计算，避免 UTC 解析偏移） */
function addDays(iso: string, n: number): string {
  const [y, m, d] = iso.split('-').map(Number)
  const dt = new Date(y, m - 1, d)
  dt.setDate(dt.getDate() + n)
  const p = (x: number) => String(x).padStart(2, '0')
  return `${dt.getFullYear()}-${p(dt.getMonth() + 1)}-${p(dt.getDate())}`
}
const nextEarliestDate = computed(() => {
  const last = meeting.state?.last_meeting?.date
  const days = meeting.state?.new_cycle_days ?? 3
  return last ? addDays(last, days) : '—'
})

/* 飞书周会群 chat_id */
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
    ElMessage.success('周会群 chat_id 已保存')
  } catch {
    ElMessage.error('保存失败（需要管理员权限）')
  } finally {
    savingChatId.value = false
  }
}

/* 周会自动开启 */
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
    if (!r.enabled && autoReminder.value) {
      try {
        const rr = await settingsApi.setAutoReminder(false)
        autoReminder.value = rr.enabled
      } catch {
        // 同步关闭催更失败不阻断主流程
      }
    }
    ElMessage.success(r.enabled ? '已开启周会自动开启' : '已关闭周会自动开启')
  } catch {
    autoOpen.value = !val
    ElMessage.error('保存失败（需要管理员权限）')
  } finally {
    savingAutoOpen.value = false
  }
}

/* 周会自动催更 */
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
    autoReminder.value = !val
    ElMessage.error('保存失败（需要管理员权限）')
  } finally {
    savingAutoReminder.value = false
  }
}

async function save() {
  saving.value = true
  try {
    await meeting.setCount(editCount.value)
    editCount.value = meeting.state?.this_week_count ?? editCount.value
    ElMessage.success('周会次数已校准')
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail || '保存失败（需要管理员权限）')
  } finally {
    saving.value = false
  }
}

async function load() {
  loading.value = true
  try {
    await meeting.load()
    editCount.value = meeting.state?.this_week_count ?? 0
  } finally {
    loading.value = false
  }
  await loadCoreChatId()
  await loadAutoOpen()
  await loadAutoReminder()
}

onMounted(load)
</script>

<style scoped>
.meeting-settings { padding: var(--sp-2) 0; }
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
.info-block { display: flex; flex-direction: column; gap: var(--sp-3); margin-bottom: var(--sp-4); }
.info-row { display: flex; align-items: center; gap: var(--sp-3); }
.ilabel { width: 96px; flex-shrink: 0; color: var(--c-ink-3); font-size: 13px; }
.ival { color: var(--c-ink); font-weight: 500; }
.ival.ok { color: #1a73e8; font-weight: 600; }
.calibrate { display: flex; align-items: center; gap: var(--sp-3); padding-top: var(--sp-3); border-top: 1px solid var(--c-border); }
.hint { font-size: 12px; }
.tip { margin: var(--sp-3) 0 0; font-size: 12px; line-height: 1.6; }
</style>
