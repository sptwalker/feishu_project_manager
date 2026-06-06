<template>
  <header class="mr-top">
    <!-- 左：会议信息 + 总时长 -->
    <div class="mr-left">
      <div class="mr-left-row">
        <b class="mr-title">周例会 · 第 {{ session }} 次</b>
        <span class="mr-total" :class="{ overtime: store.totalOvertime }">总 {{ fmt(store.totalRemaining) }}</span>
      </div>
      <span class="mr-date">{{ today }}</span>
    </div>

    <!-- 中：梯形主席台（上宽下窄） -->
    <div class="mr-podium">
      <!-- 箭头：无底色、深色、加大、垂直居中、左右拉开到两侧 -->
      <button class="mr-arrow mr-arrow-l" :disabled="store.currentPresenterIndex <= 0"
        title="上一位" @click="store.prevPresenter()">‹</button>

      <div class="mr-center">
        <div class="mr-name">
          <span class="mr-dept" :style="{ color: deptColor }">{{ presenter?.dept || '—' }}</span>
          <span class="mr-sep">|</span>
          <span class="mr-nm">{{ presenter?.member || '—' }}</span>
        </div>
        <!-- 本人时间：无底色、放大、按时长分级配色，>15min 闪烁 -->
        <span class="mr-person" :class="{ flashing: personFlashing }" :style="{ color: personColor }">
          {{ fmt(store.personElapsed) }}
        </span>
      </div>

      <button class="mr-arrow mr-arrow-r" :disabled="store.currentPresenterIndex >= store.presenters.length - 1"
        title="下一位" @click="store.nextPresenter()">›</button>
    </div>

    <!-- 右：纪要 + 设置 -->
    <div class="mr-actions">
      <el-button type="primary" @click="emit('view-minutes')">查看会议纪要</el-button>
      <el-button @click="emit('open-settings')">⚙ 设置</el-button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElButton } from 'element-plus'
import { useMeetingReportStore } from '@/stores/meetingReport'

defineProps<{ session: number; today: string }>()
const emit = defineEmits<{ (e: 'view-minutes'): void; (e: 'open-settings'): void }>()

const store = useMeetingReportStore()
const presenter = computed(() => store.presenters[store.currentPresenterIndex] ?? null)

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
.mr-top { position: relative; display: flex; justify-content: space-between; align-items: flex-start;
  background: var(--c-surface, #fff); border-bottom: 2px solid var(--c-border, #e4e7ed);
  min-height: 64px; padding: 10px 16px; z-index: 5; }
.mr-left-row { display: flex; align-items: center; gap: 12px; }
.mr-title { font-size: 16px; }
.mr-date { color: var(--c-ink-3); font-size: 12px; }
.mr-total { font-size: 16px; font-weight: 800; font-variant-numeric: tabular-nums;
  color: #1a7f4b; background: #e3f5ea; padding: 2px 12px; border-radius: 6px; }
.mr-total.overtime { color: #fff; background: #d23b3b; animation: flash 1s steps(2) infinite; }
@keyframes flash { 50% { opacity: .4; } }
@media (prefers-reduced-motion: reduce) {
  .mr-total.overtime, .mr-person.flashing { animation: none; }
}

/* 梯形主席台 */
.mr-podium { position: absolute; left: 50%; transform: translateX(-50%); top: 4px;
  min-width: 360px; height: 90px; padding: 6px 24px 12px;
  background: linear-gradient(180deg, #eef1ff, #e3e8ff);
  border: 1px solid #c3ccf5; border-top: none;
  clip-path: polygon(0 0, 100% 0, 88% 100%, 12% 100%);
  box-shadow: 0 8px 18px rgba(0,0,0,.12);
  display: flex; align-items: center; justify-content: center; z-index: 6; }

/* 中部：部门·姓名（上）+ 本人时间（下） */
.mr-center { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.mr-name { display: flex; align-items: center; gap: 10px; }
.mr-dept { font-size: 15px; font-weight: 700; }
.mr-sep { color: var(--c-ink-3); font-weight: 300; }
.mr-nm { font-size: 17px; font-weight: 800; color: var(--c-ink); }
/* 本人时间：无底色、大字号、分级配色 */
.mr-person { font-size: 30px; font-weight: 800; line-height: 1; font-variant-numeric: tabular-nums; }
.mr-person.flashing { animation: flash 0.8s steps(2) infinite; }

/* 箭头：无底色、深色、加大、垂直居中、左右拉开 */
.mr-arrow { position: absolute; top: 50%; transform: translateY(-50%);
  background: transparent; border: none; padding: 0;
  font-size: 34px; line-height: 1; font-weight: 700; color: var(--c-ink);
  cursor: pointer; transition: color .15s ease, opacity .15s ease; }
.mr-arrow-l { left: 7%; }
.mr-arrow-r { right: 7%; }
.mr-arrow:hover:not(:disabled) { color: var(--c-accent, #3954d6); }
.mr-arrow:focus-visible { outline: 2px solid var(--c-accent, #3954d6); outline-offset: 2px; border-radius: 4px; }
.mr-arrow:disabled { opacity: .25; cursor: not-allowed; }

.mr-actions { display: flex; gap: 8px; }
</style>
