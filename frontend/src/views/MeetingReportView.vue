<template>
  <div class="mr-page">
    <MeetingTopBar :session="session" :today="today"
      @view-minutes="onViewMinutes" @open-settings="settingsVisible = true" />
    <div class="mr-body">
      <aside class="mr-aside"><MeetingReportTree /></aside>
      <main class="mr-main">
        <ProjectDetailContent v-if="store.currentProject" :visible="true"
          :project="store.currentProject" layout="meeting" @updated="store.load()" />
        <div v-else class="mr-empty">暂无待汇报项目</div>
      </main>
    </div>

    <el-dialog v-model="settingsVisible" title="计时设置" width="360px">
      <div class="mr-set-row">总会议时长（分钟）
        <el-input-number v-model="totalM" :min="1" :max="600" />
      </div>
      <div class="mr-set-row">单人提醒阈值（分钟）
        <el-input-number v-model="thresholdM" :min="1" :max="120" />
      </div>
      <template #footer>
        <el-button @click="settingsVisible = false">取消</el-button>
        <el-button type="primary" @click="saveSettings">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { ElDialog, ElButton, ElInputNumber, ElMessage } from 'element-plus'
import MeetingTopBar from '@/components/meeting-report/MeetingTopBar.vue'
import MeetingReportTree from '@/components/meeting-report/MeetingReportTree.vue'
import ProjectDetailContent from '@/components/ProjectDetailContent.vue'
import { useMeetingReportStore } from '@/stores/meetingReport'
import { useMeetingStore } from '@/stores/meeting'
import { settingsApi, meetingApi } from '@/api/resources'

const store = useMeetingReportStore()
const meeting = useMeetingStore()

const session = ref(0)
const today = new Date().toISOString().slice(0, 10)
const settingsVisible = ref(false)
const totalM = ref(30)
const thresholdM = ref(5)

onMounted(async () => {
  await meeting.load()
  session.value = meeting.currentCount
  await store.load()
  totalM.value = store.totalMinutes
  thresholdM.value = store.personThresholdMinutes
  store.start()
  try { await meetingApi.startReport(session.value) } catch { /* 非阻断：未开启周会时忽略 */ }
})

onBeforeUnmount(() => store.stop())

/* 超时蜂鸣（Web Audio，无需音频文件） */
function beep() {
  try {
    const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    const ctx = new Ctx()
    const osc = ctx.createOscillator()
    osc.frequency.value = 880
    osc.connect(ctx.destination)
    osc.start(); osc.stop(ctx.currentTime + 0.2)
  } catch { /* 忽略：浏览器限制或不支持 */ }
}
// 本人每满 5 分钟蜂鸣一次（300/600/900… 秒）
watch(() => store.personElapsed, (s) => { if (s > 0 && s % 300 === 0) beep() })
// 总会议时长归零提醒
watch(() => store.totalOvertime, (v, old) => { if (v && !old) beep() })

async function saveSettings() {
  await settingsApi.setMeetingTimer({ total_minutes: totalM.value, person_threshold_minutes: thresholdM.value })
  store.totalMinutes = totalM.value
  store.personThresholdMinutes = thresholdM.value
  store.totalRemaining = totalM.value * 60
  settingsVisible.value = false
  ElMessage.success('已保存')
}

async function onViewMinutes() {
  try {
    const r = await meetingApi.send(session.value)
    ElMessage[r.ok ? 'success' : 'warning'](r.message)
  } catch {
    ElMessage.error('生成纪要失败')
  }
}
</script>

<style scoped>
.mr-page { position: fixed; inset: 0; display: flex; flex-direction: column;
  background: var(--c-canvas, #f5f6f8); }
.mr-body { flex: 1; display: flex; min-height: 0; }
.mr-aside { width: 24%; min-width: 240px; border-right: 1px solid var(--c-border, #e4e7ed);
  background: var(--c-surface, #fff); padding-top: 30px; }
.mr-main { flex: 1; overflow: hidden; padding: 30px 20px 16px; }
.mr-empty { display: grid; place-items: center; height: 100%; color: var(--c-ink-3); }
.mr-set-row { display: flex; justify-content: space-between; align-items: center; margin: 12px 0; }
</style>
