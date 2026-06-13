<template>
  <div class="followup-settings" v-loading="loading">
    <!-- 项目进展催办设置：停滞天数阈值 -->
    <section class="card">
      <h3 class="card-title">项目进展催办设置</h3>
      <p class="tip muted" style="margin-top:0">
        系统按此阈值判定「进展停滞」——最新进展距今超过该天数的项目，连同存在未闭合待办的项目，
        都会出现在下方催办名单中。
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

    <!-- 手动 / 自动催办 -->
    <section class="card">
      <h3 class="card-title">手动 / 自动催办</h3>
      <p class="tip muted" style="margin-top:0">
        催办以飞书私聊直发给每个负责人。立即催办可逐个或全部发送；自动定时催办按设定的时间自动向所有需催办的负责人发送。
      </p>
      <div class="btn-row">
        <el-button type="primary" :icon="Bell" :disabled="!isAdmin" @click="manualVisible = true">立即催办</el-button>
        <el-button :icon="Timer" :disabled="!isAdmin" @click="openAuto">自动定时催办</el-button>
        <span v-if="autoCfg.enabled" class="muted hint">{{ autoSummary }}</span>
        <span v-if="!isAdmin" class="muted hint">（仅管理员可操作）</span>
      </div>
    </section>

    <!-- 立即催办确认弹窗（复用组件） -->
    <ManualFollowupDialog v-model="manualVisible" />

    <!-- 自动定时催办设置弹窗 -->
    <el-dialog v-model="autoVisible" title="自动定时催办" width="520px">
      <el-form label-width="92px">
        <el-form-item label="启用">
          <el-switch v-model="autoForm.enabled" />
        </el-form-item>
        <el-form-item label="催办方式">
          <el-radio-group v-model="autoForm.mode" :disabled="!autoForm.enabled">
            <el-radio value="weekly">每周定时</el-radio>
            <el-radio value="fixed_days">固定天数定时</el-radio>
            <el-radio value="follow_meeting">跟随周会催更</el-radio>
          </el-radio-group>
        </el-form-item>

        <template v-if="autoForm.mode === 'weekly'">
          <el-form-item label="星期">
            <el-select v-model="autoForm.weekday" :disabled="!autoForm.enabled" style="width: 140px">
              <el-option v-for="(label, i) in weekdayLabels" :key="i" :label="label" :value="i" />
            </el-select>
          </el-form-item>
          <el-form-item label="时间">
            <el-time-picker v-model="timeModel" :disabled="!autoForm.enabled" format="HH:mm" value-format="HH:mm" style="width: 140px" />
          </el-form-item>
        </template>

        <template v-else-if="autoForm.mode === 'fixed_days'">
          <el-form-item label="间隔天数">
            <el-input-number v-model="autoForm.interval_days" :min="3" :max="15" :disabled="!autoForm.enabled" controls-position="right" style="width: 140px" />
          </el-form-item>
          <el-form-item label="时间">
            <el-time-picker v-model="timeModel" :disabled="!autoForm.enabled" format="HH:mm" value-format="HH:mm" style="width: 140px" />
          </el-form-item>
        </template>

        <template v-else>
          <el-form-item label="跟随催更">
            <el-checkbox-group v-model="autoForm.follow" :disabled="!autoForm.enabled">
              <el-checkbox value="one">周五催更①</el-checkbox>
              <el-checkbox value="two">周日催更②</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
          <p class="tip muted" style="margin:0 0 0 92px">仅在周会进行中、对应催更触发时一并发送个人催办。</p>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="autoVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingAuto" @click="saveAuto">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Bell, Timer } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { settingsApi, followupApi } from '@/api/resources'
import type { FollowupAuto } from '@/types'
import ManualFollowupDialog from '@/components/ManualFollowupDialog.vue'

const auth = useAuthStore()
const isAdmin = computed(() => auth.currentUser?.role === 'admin')
const loading = ref(false)

/* 停滞天数 */
const stallDays = ref(30)
const savedStallDays = ref(30)
const savingStall = ref(false)

async function loadStallDays() {
  try {
    const r = await settingsApi.getFollowupStallDays()
    stallDays.value = r.days
    savedStallDays.value = r.days
  } catch { /* 保持默认 */ }
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

/* 立即催办（复用组件） */
const manualVisible = ref(false)

/* 自动定时催办 */
const autoVisible = ref(false)
const savingAuto = ref(false)
const weekdayLabels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const autoCfg = ref<FollowupAuto>({
  enabled: false, mode: 'weekly', weekday: 4, time: '14:00', interval_days: 7, follow: ['one'],
})
const autoForm = reactive<FollowupAuto>({
  enabled: false, mode: 'weekly', weekday: 4, time: '14:00', interval_days: 7, follow: ['one'],
})
const timeModel = computed({
  get: () => autoForm.time || '14:00',
  set: (v: string) => { autoForm.time = v || '14:00' },
})

const autoSummary = computed(() => {
  const c = autoCfg.value
  if (!c.enabled) return ''
  if (c.mode === 'weekly') return `已启用：每${weekdayLabels[c.weekday] || ''} ${c.time}`
  if (c.mode === 'fixed_days') return `已启用：每 ${c.interval_days} 天 ${c.time}`
  return `已启用：跟随周会催更（${(c.follow || []).map((f) => f === 'one' ? '周五①' : '周日②').join('、') || '未选'}）`
})

async function loadAuto() {
  try {
    autoCfg.value = await followupApi.getAuto()
  } catch { /* 保持默认 */ }
}

function openAuto() {
  Object.assign(autoForm, autoCfg.value)
  if (!autoForm.follow) autoForm.follow = []
  autoVisible.value = true
}

async function saveAuto() {
  savingAuto.value = true
  try {
    const r = await followupApi.setAuto({ ...autoForm })
    autoCfg.value = r
    ElMessage.success('自动催办设置已保存')
    autoVisible.value = false
  } catch {
    ElMessage.error('保存失败（需要管理员权限）')
  } finally {
    savingAuto.value = false
  }
}

onMounted(async () => {
  loading.value = true
  try {
    await loadStallDays()
    await loadAuto()
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.followup-settings { padding: var(--sp-2) 0; }
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
.calibrate { display: flex; align-items: center; gap: var(--sp-3); }
.ilabel { width: 96px; flex-shrink: 0; color: var(--c-ink-3); font-size: 13px; }
.btn-row { display: flex; align-items: center; gap: var(--sp-3); flex-wrap: wrap; }
.hint { font-size: 12px; }
.tip { font-size: 12px; line-height: 1.6; }
</style>
