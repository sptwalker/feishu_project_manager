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

    <!-- 中：梯形主席台（上大下小） -->
    <div class="mr-podium">
      <div class="mr-presenter">
        <button class="mr-arrow" :disabled="store.currentPresenterIndex <= 0" @click="store.prevPresenter()">‹</button>
        <div class="mr-name">
          <span class="mr-dept">{{ presenter?.dept || '—' }}</span>
          <span class="mr-nm">{{ presenter?.member || '—' }}</span>
        </div>
        <button class="mr-arrow" :disabled="store.currentPresenterIndex >= store.presenters.length - 1" @click="store.nextPresenter()">›</button>
      </div>
      <span class="mr-person" :class="{ overtime: store.personOvertime }">本人 {{ fmt(store.personElapsed) }}</span>
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
.mr-total.overtime, .mr-person.overtime { color: #fff; background: #d23b3b; animation: flash 1s steps(2) infinite; }
@keyframes flash { 50% { opacity: .45; } }
/* 降低动效偏好：不闪烁，改为静态高对比红底白字（仍醒目，不刺激） */
@media (prefers-reduced-motion: reduce) {
  .mr-total.overtime, .mr-person.overtime { animation: none; }
}
.mr-podium { position: absolute; left: 50%; transform: translateX(-50%); top: 6px;
  min-width: 320px; padding: 10px 22px 14px;
  background: linear-gradient(180deg, #eef1ff, #e3e8ff);
  border: 1px solid #c3ccf5; border-top: none;
  clip-path: polygon(0 0, 100% 0, 88% 100%, 12% 100%);
  box-shadow: 0 8px 18px rgba(0,0,0,.12);
  display: flex; flex-direction: column; align-items: center; gap: 8px; z-index: 6; }
.mr-presenter { display: flex; align-items: center; gap: 12px; }
.mr-arrow { width: 28px; height: 28px; border-radius: 50%; border: none; background: var(--c-accent, #3954d6);
  color: #fff; font-size: 16px; font-weight: 800; cursor: pointer; transition: filter .15s ease; }
.mr-arrow:hover:not(:disabled) { filter: brightness(1.08); }
.mr-arrow:focus-visible { outline: 2px solid var(--c-accent, #3954d6); outline-offset: 2px; }
.mr-arrow:disabled { opacity: .35; cursor: not-allowed; }
.mr-name { display: flex; align-items: center; gap: 8px; }
.mr-dept { background: var(--c-accent, #3954d6); color: #fff; padding: 1px 8px; border-radius: 4px; font-size: 12px; }
.mr-nm { font-size: 18px; font-weight: 800; }
.mr-person { font-size: 15px; font-weight: 800; font-variant-numeric: tabular-nums;
  color: #8a5a00; background: #fff1d6; padding: 2px 14px; border-radius: 6px; }
.mr-actions { display: flex; gap: 8px; }
</style>
