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
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElDialog, ElButton, ElInputNumber, ElCheckbox, ElMessage, ElMessageBox } from 'element-plus'
import MeetingTopBar from '@/components/meeting-report/MeetingTopBar.vue'
import MeetingReportTree from '@/components/meeting-report/MeetingReportTree.vue'
import ProjectDetailContent from '@/components/ProjectDetailContent.vue'
import ProjectDetailDrawer from '@/components/ProjectDetailDrawer.vue'
import { useMeetingReportStore } from '@/stores/meetingReport'
import { useMeetingStore } from '@/stores/meeting'
import { settingsApi, meetingApi } from '@/api/resources'

const router = useRouter()
const store = useMeetingReportStore()
const meeting = useMeetingStore()

const session = ref(0)
const today = new Date().toISOString().slice(0, 10)
const settingsVisible = ref(false)
const createVisible = ref(false)
const totalM = ref(120)
const thresholdM = ref(5)
const soundEnabled = ref(true)   // 声音提醒开关：默认开；关闭后不再播放任何逾时提示音

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

async function onViewMinutes() {
  try {
    const r = await meetingApi.send(session.value)
    ElMessage[r.ok ? 'success' : 'warning'](r.message)
  } catch {
    ElMessage.error('生成纪要失败')
  }
}

/* 结束会议：确认后归档（记录结束时间）+ 关闭周会模式，再离开汇报页 */
async function onEndMeeting() {
  try {
    await ElMessageBox.confirm('确定结束本次周会？将记录结束时间并关闭周会模式。', '结束会议', {
      type: 'warning', confirmButtonText: '结束会议', cancelButtonText: '取消',
    })
  } catch {
    return  // 用户取消
  }
  try {
    await meetingApi.close()  // 后端：归档写 ended_at + set_active(false) + 记操作日志
    store.stop()
    ElMessage.success('周会已结束')
  } catch {
    ElMessage.error('结束会议失败（需要管理员权限）')
  } finally {
    router.push('/board')  // 关闭汇报页
  }
}
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
