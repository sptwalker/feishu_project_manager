<template>
  <div class="mr-page">
    <MeetingTopBar :session="session" :today="today"
      @view-minutes="onViewMinutes" @open-settings="settingsVisible = true" @end-meeting="onEndMeeting" />
    <div class="mr-body">
      <aside class="mr-aside"><MeetingReportTree /></aside>
      <main class="mr-main">
        <ProjectDetailContent v-if="store.currentProject" :visible="true"
          :project="store.currentProject" layout="meeting" @updated="store.load()">
          <template #header-extra>
            <!-- 新增项目：复用抽屉的 createMode 新建流程；琥珀色、与项目编辑按钮同尺寸 -->
            <el-button size="large" class="mr-add-btn" @click="createVisible = true">＋ 新增项目</el-button>
          </template>
          <template #title-after>
            <!-- 项目翻页：本人范围内 ‹ ›；翻到尽头再出现跨汇报人按钮 ‹‹ ››（同款字符双写，与单项目翻页一致） -->
            <span class="mr-proj-nav">
              <!-- 向前翻到本人第一个项目后：出现「‹‹」跳上一位汇报人（无上一位则不显示） -->
              <button v-if="store.currentProjectIndexInMember <= 0 && store.currentPresenterIndex > 0"
                class="mr-proj-arrow mr-proj-arrow-jump" title="上一位汇报人"
                @click="store.prevPresenterTail()">‹‹</button>
              <button class="mr-proj-arrow" title="上一个项目"
                :disabled="store.currentProjectIndexInMember <= 0"
                @click="store.prevProjectInMember()">‹</button>
              <button class="mr-proj-arrow" title="下一个项目"
                :disabled="store.currentProjectIndexInMember >= store.currentMemberProjects.length - 1"
                @click="store.nextProjectInMember()">›</button>
              <!-- 向后翻到本人最后一个项目后：出现「››」跳下一位汇报人（无下一位则不显示） -->
              <button v-if="store.currentProjectIndexInMember >= store.currentMemberProjects.length - 1 && store.currentPresenterIndex < store.presenters.length - 1"
                class="mr-proj-arrow mr-proj-arrow-jump" title="下一位汇报人"
                @click="store.nextPresenter()">››</button>
            </span>
          </template>
        </ProjectDetailContent>
        <div v-else class="mr-empty">暂无待汇报项目</div>
      </main>
    </div>

    <el-dialog v-model="settingsVisible" title="计时设置" width="360px">
      <div class="mr-set-row">总时长提醒（分钟）
        <el-input-number v-model="totalM" :min="1" :max="600" />
      </div>
      <div class="mr-set-row">单人提醒阈值（分钟）
        <el-input-number v-model="thresholdM" :min="1" :max="120" />
      </div>
      <div class="mr-set-row mr-set-sound">声音提醒
        <el-checkbox v-model="soundEnabled" />
      </div>
      <template #footer>
        <el-button @click="settingsVisible = false">取消</el-button>
        <el-button type="primary" @click="saveSettings">保存</el-button>
      </template>
    </el-dialog>

    <!-- 新增项目：复用 ProjectDetailDrawer 的 createMode 新建流程，保存后刷新左树 -->
    <ProjectDetailDrawer v-model:visible="createVisible" :project="null" create-mode @updated="store.load()" />

    <!-- 查看会议纪要：复用「周会记录」弹窗，本地展示本次纪要内容，弹窗内可发送到飞书 -->
    <MeetingRecordDialog v-model:visible="recordVisible" :session="session" />

    <!-- 会议结束：各汇报人用时统计柱状图 -->
    <el-dialog v-model="statsVisible" title="本次周会汇报人用时统计" width="680px" :close-on-click-modal="false" @closed="onStatsClosed">
      <BaseChart v-if="statsData.length" :option="statsOption" style="height: 360px" />
      <el-empty v-else description="本次周会暂无计时记录" />
      <template #footer>
        <el-button type="primary" @click="statsVisible = false">完成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElDialog, ElButton, ElInputNumber, ElCheckbox, ElMessage, ElMessageBox } from 'element-plus'
import MeetingTopBar from '@/components/meeting-report/MeetingTopBar.vue'
import MeetingReportTree from '@/components/meeting-report/MeetingReportTree.vue'
import ProjectDetailContent from '@/components/ProjectDetailContent.vue'
import ProjectDetailDrawer from '@/components/ProjectDetailDrawer.vue'
import MeetingRecordDialog from '@/components/MeetingRecordDialog.vue'
import BaseChart from '@/components/BaseChart.vue'
import { useMeetingReportStore } from '@/stores/meetingReport'
import { useMeetingStore } from '@/stores/meeting'
import { useAuthStore } from '@/stores/auth'
import { settingsApi, meetingApi } from '@/api/resources'

const router = useRouter()
const store = useMeetingReportStore()
const meeting = useMeetingStore()
const auth = useAuthStore()
const isAdmin = computed(() => auth.currentUser?.role === 'admin')

const session = ref(0)
const today = new Date().toISOString().slice(0, 10)
const settingsVisible = ref(false)
const createVisible = ref(false)
const recordVisible = ref(false)   // 查看会议纪要弹窗（本地展示本次周会记录，飞书发送在弹窗内按钮）
const totalM = ref(120)
const thresholdM = ref(5)
const soundEnabled = ref(true)   // 声音提醒开关：默认开；关闭后不再播放任何逾时提示音

// 会议结束：各汇报人用时统计柱状图弹窗
const statsVisible = ref(false)
const statsData = ref<{ name: string; seconds: number }[]>([])

onMounted(async () => {
  await meeting.load()
  session.value = meeting.currentCount
  await store.load()
  totalM.value = store.totalMinutes
  thresholdM.value = store.personThresholdMinutes
  try { if (isAdmin.value) await meetingApi.startReport(session.value) } catch { /* 非阻断：未开启周会时忽略 */ }
  // 连接服务端计时：管理员认领主控，其余协助态；启动 tick/轮询/心跳
  await store.connectTimer(isAdmin.value)
})

onBeforeUnmount(() => store.disconnectTimer())

/* 超时蜂鸣（Web Audio，无需音频文件）；声音提醒关闭时直接跳过 */
function beep() {
  if (!soundEnabled.value) return
  try {
    const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    const ctx = new Ctx()
    const osc = ctx.createOscillator()
    osc.frequency.value = 880
    osc.connect(ctx.destination)
    osc.start(); osc.stop(ctx.currentTime + 0.2)
  } catch { /* 忽略：浏览器限制或不支持 */ }
}
// 本人每满 5 分钟蜂鸣一次（仅连续计时触发；切换汇报人导致的跳变不算）
let lastPersonElapsed = 0
watch(() => store.personElapsed, (s) => {
  const isTick = s === lastPersonElapsed + 1
  lastPersonElapsed = s
  if (isTick && s > 0 && s % 300 === 0) beep()
})
// 总会议时长归零提醒
watch(() => store.totalOvertime, (v, old) => { if (v && !old) beep() })

async function saveSettings() {
  await settingsApi.setMeetingTimer({ total_minutes: totalM.value, person_threshold_minutes: thresholdM.value })
  store.totalMinutes = totalM.value
  store.personThresholdMinutes = thresholdM.value
  settingsVisible.value = false
  ElMessage.success('已保存')
}

/* 查看会议纪要：打开本次周会记录弹窗（本地展示，不依赖飞书）；
   生成飞书云文档并分享到核心群的功能，保留在弹窗内的「发送会议记录」按钮 */
function onViewMinutes() {
  recordVisible.value = true
}

/* 结束会议：确认 → 捕获各汇报人用时快照 → 归档关闭 → 弹统计柱状图（关闭后再清理跳转） */
async function onEndMeeting() {
  try {
    await ElMessageBox.confirm('确定结束本次周会？将记录结束时间并关闭周会模式。', '结束会议', {
      type: 'warning', confirmButtonText: '结束会议', cancelButtonText: '取消',
    })
  } catch {
    return  // 用户取消
  }
  // 结束前捕获各汇报人累计用时（服务端锚点推算的当前值），按用时降序
  const snapshot = Object.entries(store.personTimes)
    .map(([key, seconds]) => ({ name: key.split('|')[1] || key, seconds: seconds as number }))
    .filter((x) => x.seconds > 0)
    .sort((a, b) => b.seconds - a.seconds)
  try {
    await meetingApi.close()  // 后端：归档写 ended_at + set_active(false) + 清空 timer + 记操作日志
    ElMessage.success('周会已结束')
  } catch {
    ElMessage.error('结束会议失败（需要管理员权限）')
  } finally {
    store.reset()       // 停定时器 + 清浏览/角色/过滤
    lastPersonElapsed = 0  // 重置蜂鸣节流基准
    if (snapshot.length) {
      statsData.value = snapshot
      statsVisible.value = true   // 有数据则弹统计图，关闭后跳转
    } else {
      router.push('/board')
    }
  }
}

/* 关闭统计图后离开汇报页 */
function onStatsClosed() {
  statsVisible.value = false
  router.push('/board')
}

/* 汇报人用时柱状图配置（秒 → 自适应 分:秒 标签） */
const statsOption = computed(() => {
  const names = statsData.value.map((x) => x.name)
  const values = statsData.value.map((x) => x.seconds)
  const fmtMMSS = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: (p: { name: string; value: number }[]) => `${p[0].name}：${fmtMMSS(p[0].value)}` },
    grid: { left: 8, right: 24, top: 16, bottom: 8, containLabel: true },
    xAxis: { type: 'category', data: names, axisLabel: { interval: 0, rotate: names.length > 6 ? 35 : 0 } },
    yAxis: { type: 'value', name: '用时', axisLabel: { formatter: (v: number) => fmtMMSS(v) } },
    series: [{
      type: 'bar', barWidth: '46%',
      data: values.map((v, i) => ({ value: v, itemStyle: { color: ['#1A73E8', '#2F8FE0', '#13C2C2', '#3B6FE0', '#5AB1BB', '#2F54EB', '#41B0D8', '#6979F8'][i % 8], borderRadius: [4, 4, 0, 0] } })),
      label: { show: true, position: 'top', formatter: (p: { value: number }) => fmtMMSS(p.value) },
    }],
  } as Record<string, unknown>
})
</script>

<style scoped>
.mr-page { position: fixed; inset: 0; display: flex; flex-direction: column;
  background: var(--c-canvas, #f5f6f8); }
.mr-body { flex: 1; display: flex; min-height: 0; }
.mr-aside { width: 24%; min-width: 240px; border-right: 1px solid var(--c-border, #e4e7ed);
  background: var(--c-surface, #fff); padding-top: 8px; }
.mr-main { flex: 1; overflow: hidden; padding: 30px 20px 16px; }
.mr-empty { display: grid; place-items: center; height: 100%; color: var(--c-ink-3); }
.mr-set-row { display: flex; justify-content: space-between; align-items: center; margin: 12px 0; }
/* 声音提醒：勾选框紧跟文字（不像数字行那样两端分散） */
.mr-set-sound { justify-content: flex-start; gap: 10px; }
/* 项目名后的无边框翻页按钮（当前负责人范围内切换上/下一个项目）：加大加深更醒目 */
.mr-proj-nav { display: inline-flex; align-items: center; gap: 6px; margin-left: 14px; vertical-align: middle; }
.mr-proj-arrow { background: transparent; border: none; padding: 0 8px;
  font-size: 30px; line-height: 1; font-weight: 800; color: var(--c-ink-2, #5a6072);
  cursor: pointer; transition: color .15s ease; }
.mr-proj-arrow:hover:not(:disabled) { color: var(--c-accent, #3954d6); }
.mr-proj-arrow:disabled { opacity: .3; cursor: not-allowed; }
/* 跨汇报人翻页（‹‹ ››）：与项目内翻页 ‹ › 完全同字符/字体/字号；轻微负字距让双箭头更紧凑 */
.mr-proj-arrow-jump { letter-spacing: -3px; padding-right: 11px; }
/* 新增项目按钮：琥珀色，尺寸与「项目编辑」按钮一致（layout-meeting 下 34px） */
.mr-add-btn { height: 34px; padding: 0 14px; font-size: 14px;
  background: #f59e0b; border-color: #f59e0b; color: #fff; }
.mr-add-btn:hover, .mr-add-btn:focus { background: #d98c08; border-color: #d98c08; color: #fff; }
</style>
