<template>
  <header class="mr-top">
    <!-- 左：会议信息 + 总时间 + 计时控制 + 统计 -->
    <div class="mr-left">
      <span class="mr-meet">周例会 · 第 {{ session }} 次 · {{ today }}</span>
      <span class="mr-total" :class="{ overtime: store.totalOvertime }">总 {{ fmt(store.totalElapsed) }}</span>
      <!-- 计时控制（无边框）：▶ 开始/继续 · ❚❚ 暂停；仅主控可点 -->
      <button class="mr-timer-btn" :class="{ running: store.running }"
        :disabled="!store.isController" :title="timerBtnTitle" @click="onToggleTiming">
        {{ store.running ? '❚❚' : '▶' }}
      </button>
      <!-- 统计：弹窗显示各汇报人当前用时（所有人可看） -->
      <button class="mr-stat-btn" title="汇报人用时统计" @click="statsVisible = true">📊</button>
    </div>

    <!-- 中：梯形主席台（上宽下窄） -->
    <div class="mr-podium">
      <!-- 箭头：无底色、深色、加大、垂直居中、左右拉开到两侧 -->
      <button class="mr-arrow mr-arrow-l" :disabled="store.currentPresenterIndex <= 0"
        title="上一位" @click="store.prevPresenter()">‹</button>

      <div class="mr-center">
        <span class="mr-dept" :style="{ color: deptColor }">{{ presenter?.dept || '—' }}</span>
        <span class="mr-sep">|</span>
        <span class="mr-nm">{{ presenter?.member || '—' }}</span>
        <span class="mr-sep">|</span>
        <!-- 本人时间：无底色、按时长分级配色，≥15min 闪烁 -->
        <span class="mr-person" :class="{ flashing: personFlashing }" :style="{ color: personColor }">
          {{ fmt(store.personElapsed) }}
        </span>
      </div>

      <button class="mr-arrow mr-arrow-r" :disabled="store.currentPresenterIndex >= store.presenters.length - 1"
        title="下一位" @click="store.nextPresenter()">›</button>
    </div>

    <!-- 右：角色/接管 + 纪要 + 结束会议 + 设置 -->
    <div class="mr-actions">
      <!-- 主控角色标 -->
      <span v-if="store.isController" class="mr-role mr-role-ctrl">● 主控</span>
      <!-- 协助态：只读提示 + 主控释放后可接管 -->
      <template v-else-if="store.timer?.active">
        <span v-if="store.controllerReleased" class="mr-role mr-role-warn">主控已掉线</span>
        <span v-else class="mr-role mr-role-assist">● 协助中</span>
        <el-button v-if="store.controllerReleased" type="primary" size="small" @click="onTakeover">接管控制</el-button>
      </template>

      <el-button type="primary" @click="emit('view-minutes')">查看会议纪要</el-button>
      <el-button class="mr-end-btn" @click="emit('end-meeting')">结束会议</el-button>
      <el-button @click="emit('open-settings')">⚙ 设置</el-button>
    </div>
  </header>

  <!-- 主控掉线横幅：计时已自动暂停，等待重连 -->
  <div v-if="store.controllerOffline" class="mr-offline-banner">
    ⚠ 主控客户端掉线，计时已自动暂停，等待重连（超 3 分钟后可由其他端接管）
  </div>

  <!-- 汇报人用时统计弹窗（会议中实时查看） -->
  <el-dialog v-model="statsVisible" title="汇报人用时统计" width="640px">
    <BaseChart v-if="store.personTimeStats.length" :option="statsOption" style="height: 340px" />
    <el-empty v-else description="暂无计时记录" :image-size="60" />
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElButton, ElDialog, ElEmpty, ElMessageBox, ElMessage } from 'element-plus'
import { useMeetingReportStore } from '@/stores/meetingReport'
import BaseChart from '@/components/BaseChart.vue'
import { buildPersonTimesBarOption } from '@/utils/meetingStats'

defineProps<{ session: number; today: string }>()
const emit = defineEmits<{ (e: 'view-minutes'): void; (e: 'open-settings'): void; (e: 'end-meeting'): void }>()

const store = useMeetingReportStore()
const presenter = computed(() => store.presenters[store.currentPresenterIndex] ?? null)

/* 统计弹窗：各汇报人当前用时柱状图（实时） */
const statsVisible = ref(false)
const statsOption = computed(() => buildPersonTimesBarOption(store.personTimeStats))

/* 计时控制按钮提示文案（仅主控可操作） */
const timerBtnTitle = computed(() => {
  if (!store.isController) return '仅主控可控制计时'
  return store.running ? '暂停计时' : (store.timer?.status === 'paused' ? '继续计时' : '开始计时')
})

/* ▶/❚❚ 切换：主控开始(或继续)/暂停计时 */
function onToggleTiming() {
  if (!store.isController) return
  if (store.running) store.pauseTiming()
  else store.startTiming()
}

/* 协助端接管主控：二次确认后调用（主控掉线超 3 分钟、已释放时可点） */
async function onTakeover() {
  try {
    await ElMessageBox.confirm('主控已掉线超过 3 分钟，确认接管控制权？接管后由你控制计时。', '接管控制', {
      type: 'warning', confirmButtonText: '确认接管', cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await store.takeoverControl()
  if (store.isController) ElMessage.success('已接管控制权')
  else ElMessage.warning('接管失败，可能已被他人接管')
}

/* 当前汇报人所属部门的主题色（无对应部门时回退墨色） */
const deptColor = computed(() => {
  const d = presenter.value?.dept
  return (d && store.findDepartment(d)?.color) || 'var(--c-ink)'
})

/* 本人汇报时长分级配色：<5min 黑 / <10min 深棕 / <15min 暗红 / ≥15min 鲜红 */
const personColor = computed(() => {
  const s = store.personElapsed
  if (s < 5 * 60) return '#1a1a1a'
  if (s < 10 * 60) return '#7a4a1e'
  if (s < 15 * 60) return '#9b1c1c'
  return '#ff2020'
})
/* ≥15min 闪烁 */
const personFlashing = computed(() => store.personElapsed >= 15 * 60)

/* 秒 → mm:ss */
function fmt(total: number): string {
  const s = Math.max(0, Math.floor(total))
  const m = Math.floor(s / 60)
  const r = s % 60
  return `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`
}
</script>

<style scoped>
.mr-top { position: relative; display: flex; justify-content: space-between; align-items: center;
  background: var(--c-surface, #fff); border-bottom: 2px solid var(--c-border, #e4e7ed);
  min-height: 64px; padding: 8px 16px; z-index: 5; }
.mr-left { display: flex; align-items: center; gap: 14px; }
.mr-meet { font-size: 16px; font-weight: 700; color: var(--c-ink); }
.mr-total { font-size: 17px; font-weight: 800; font-variant-numeric: tabular-nums;
  color: #1a7f4b; background: #e3f5ea; padding: 3px 14px; border-radius: 6px; }
/* 总时间超过提醒阈值：暗红数字 + 淡黄背景（不闪烁） */
.mr-total.overtime { color: #9b1c1c; background: #fdf3c4; }
/* 计时控制按钮（▶/❚❚）：无边框、圆形点击区，主控绿色、暂停态橙色 */
.mr-timer-btn { background: transparent; border: none; cursor: pointer;
  font-size: 20px; line-height: 1; color: #1a7f4b; padding: 4px 6px; border-radius: 6px;
  transition: background .15s ease, color .15s ease; }
.mr-timer-btn:hover:not(:disabled) { background: var(--c-surface-2, #f2f3f5); }
.mr-timer-btn.running { color: #d97706; }
.mr-timer-btn:disabled { opacity: .3; cursor: not-allowed; }
/* 统计按钮：无边框图标 */
.mr-stat-btn { background: transparent; border: none; cursor: pointer;
  font-size: 18px; line-height: 1; padding: 4px 6px; border-radius: 6px;
  transition: background .15s ease; }
.mr-stat-btn:hover { background: var(--c-surface-2, #f2f3f5); }
@keyframes flash { 50% { opacity: .4; } }
@media (prefers-reduced-motion: reduce) {
  .mr-person.flashing { animation: none; }
}

/* 梯形主席台（上宽下窄）：加宽、降高与上框线对齐、文字单排 */
.mr-podium { position: absolute; left: 50%; transform: translateX(-50%); top: 4px;
  min-width: 468px; height: 58px; padding: 0 30px;
  background: linear-gradient(180deg, #eef1ff, #e3e8ff);
  border: 1px solid #c3ccf5; border-top: none;
  clip-path: polygon(0 0, 100% 0, 92% 100%, 8% 100%);
  box-shadow: 0 6px 14px rgba(0,0,0,.10);
  display: flex; align-items: center; justify-content: center; z-index: 6; }

/* 中部单排：部门 | 汇报人 | 个人时间 */
.mr-center { display: flex; flex-direction: row; align-items: center; gap: 12px; }
.mr-dept { font-size: 18px; font-weight: 700; }
.mr-sep { color: var(--c-ink-3); font-weight: 300; }
.mr-nm { font-size: 20px; font-weight: 800; color: var(--c-ink); }
/* 本人时间：无底色、大字号、分级配色 */
.mr-person { font-size: 26px; font-weight: 800; line-height: 1; font-variant-numeric: tabular-nums; }
.mr-person.flashing { animation: flash 0.8s steps(2) infinite; }

/* 箭头：无底色、深色、加大、垂直居中、左右拉开 */
.mr-arrow { position: absolute; top: 50%; transform: translateY(-50%);
  background: transparent; border: none; padding: 0;
  font-size: 32px; line-height: 1; font-weight: 700; color: var(--c-ink);
  cursor: pointer; transition: color .15s ease, opacity .15s ease; }
.mr-arrow-l { left: 6%; }
.mr-arrow-r { right: 6%; }
.mr-arrow:hover:not(:disabled) { color: var(--c-accent, #3954d6); }
.mr-arrow:focus-visible { outline: 2px solid var(--c-accent, #3954d6); outline-offset: 2px; border-radius: 4px; }
.mr-arrow:disabled { opacity: .25; cursor: not-allowed; }

.mr-actions { display: flex; gap: 8px; align-items: center; }
/* 角色徽标 */
.mr-role { font-size: 13px; font-weight: 700; white-space: nowrap; padding: 0 4px; }
.mr-role-ctrl { color: #1a7f4b; }
.mr-role-assist { color: #1a73e8; }
.mr-role-warn { color: #e6493a; }
/* 主控掉线横幅 */
.mr-offline-banner {
  background: #fdf3c4; color: #9b1c1c; font-weight: 600; font-size: 14px;
  text-align: center; padding: 6px 16px; border-bottom: 1px solid #f0d98c;
}
/* 结束会议：白字灰底 */
.mr-end-btn { background: #909399; border-color: #909399; color: #fff; }
.mr-end-btn:hover, .mr-end-btn:focus { background: #7d8085; border-color: #7d8085; color: #fff; }
</style>
