<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">项目看板</h1>
        <p class="muted">{{ subtitle }}</p>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats">
      <div class="stat-card">
        <span class="stat-label">项目总数</span>
        <span class="stat-num num">{{ boardStats.total }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">进行中</span>
        <span class="stat-num num" style="color: var(--c-status-progress)">{{ boardStats.inProgress }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">已完成</span>
        <span class="stat-num num" style="color: var(--c-status-done)">{{ boardStats.completed }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">待确认项目</span>
        <span class="stat-num num" style="color: #E6A23C">{{ boardStats.pending }}</span>
      </div>
      <div class="stat-card gauge-card">
        <div class="gauge-left">
          <span class="stat-label">反馈及时度</span>
          <span class="stat-num num" :style="{ color: timelinessColor }">{{ boardStats.timeliness }}%</span>
        </div>
        <div class="gauge-box"><BaseChart :option="timelinessGauge" :height="52" /></div>
      </div>
    </div>

    <!-- 可视化图表 -->
    <div v-if="allProjects.length" class="charts">
      <div class="chart-card">
        <h3 class="chart-title">各部门项目数量</h3>
        <BaseChart :option="deptOption" :height="220" />
      </div>
      <div class="chart-card">
        <h3 class="chart-title">各负责人项目数量</h3>
        <BaseChart :option="ownerOption" :height="220" />
      </div>
    </div>

    <!-- 滚动信息流：最新进展 / 待处理事项 -->
    <div v-if="allProjects.length" class="feeds">
      <section class="feed feed-latest">
        <h3 class="feed-title">最新项目进展信息</h3>
        <div class="feed-viewport">
          <ul v-if="latestFeed.length" class="feed-track">
            <li
              v-for="(it, i) in [...latestFeed, ...latestFeed]" :key="i"
              class="feed-row" @click="openFeedItem(it)"
            >
              <span class="fr-proj">【{{ it.projectName }}】</span>
              <span class="fr-main">
                <span class="fr-date num">{{ it.time.slice(0, 10) }}</span>
                <span class="fr-status" :style="{ color: progressColor(it.status) }">【{{ it.status }}】</span>
                <span class="fr-content">{{ it.content }}</span>
              </span>
              <span class="fr-owner">{{ it.ownerName }}</span>
            </li>
          </ul>
          <div v-else class="feed-empty muted">暂无进展记录</div>
        </div>
      </section>

      <section class="feed feed-pending">
        <div class="feed-head">
          <h3 class="feed-title">待处理事项信息</h3>
          <el-button v-if="isAdmin" type="primary" size="small" :icon="Bell" @click="manualFollowupVisible = true">立即催办</el-button>
        </div>
        <div class="feed-viewport">
          <ul v-if="pendingFeed.length" class="feed-track">
            <li
              v-for="(it, i) in [...pendingFeed, ...pendingFeed]" :key="i"
              class="feed-row" @click="openFeedItem(it)"
            >
              <span class="fr-proj">【{{ it.projectName }}】</span>
              <span class="fr-main">
                <span class="fr-date num">{{ it.time.slice(0, 10) }}</span>
                <span class="fr-status" :style="{ color: progressColor(it.status) }">【{{ it.status }}】</span>
                <span class="fr-content">{{ it.content }}</span>
              </span>
              <span class="fr-owner">{{ it.ownerName }}</span>
            </li>
          </ul>
          <div v-else class="feed-empty muted">暂无待处理事项</div>
        </div>
      </section>
    </div>

    <div v-loading="loading" class="zones">
      <section v-for="z in zones" :key="z.key" class="zone" :class="`zone-${z.key}`">
        <div class="zone-head">
          <h3 class="zone-title">{{ z.title }}<span class="zone-count">{{ z.items.length }}</span></h3>
          <span class="zone-desc muted">{{ z.desc }}</span>
          <el-radio-group v-if="z.key === 'key'" v-model="viewMode" class="zone-switch" size="small">
            <el-radio-button value="grid"><el-icon><Grid /></el-icon></el-radio-button>
            <el-radio-button value="list"><el-icon><List /></el-icon></el-radio-button>
          </el-radio-group>
        </div>
        <div v-if="z.items.length" :class="viewMode === 'grid' ? 'grid' : 'list'">
          <el-tooltip
            v-for="p in z.items"
            :key="p.id"
            placement="right" effect="light" popper-class="progress-tip"
            :disabled="!p._recent.length"
          >
            <template #content>
              <div class="ptip">
                <div v-if="p._hasMore" class="ptip-more">……</div>
                <div v-for="(e, i) in p._recent" :key="i" class="ptip-item">
                  <span class="ptip-time">{{ e.time || '—' }}</span>
                  <span class="ptip-text"><span v-if="e.meeting_session" class="ptip-meeting">【第{{ e.meeting_session }}次周会更新】</span>{{ e.content }}</span>
                </div>
              </div>
            </template>
            <article
              class="project-card"
              :style="{ '--bar': z.barColor(p) }"
              @click="openDetail(p)"
            >
              <div class="pc-top">
                <h3 class="pc-name">{{ p.name }}</h3>
                <span class="pc-top-tags">
                  <span v-if="p._latest" class="pc-status" :style="{ color: progressColor(p._latest?.status) }">【{{ p._latest?.status }}】</span>
                  <span v-if="overdue(p)" class="overdue-tag">逾期</span>
                </span>
              </div>
              <div class="pc-meta">
                <span class="badge" :style="{ color: statusColor(p.status), background: 'var(--c-surface-2)' }">
                  {{ statusLabel(p.status) }}
                </span>
                <span :style="{ color: urgColor(p.urgency), fontWeight: 600 }">· {{ urgencyText(p.urgency) }}</span>
                <span v-if="p.department" class="muted">· {{ p.department }}</span>
                <span v-if="p.owner_name" class="muted">· {{ p.owner_name }}</span>
              </div>
              <div class="pc-progress">
                <span v-if="p.is_long_term" class="pc-longterm">长期项目</span>
                <template v-else>
                  <div class="bar"><div class="bar-fill" :style="{ width: p.completion + '%', background: completionGradient(p.completion) }" /></div>
                  <span class="num pc-pct">{{ p.completion }}%</span>
                </template>
              </div>
            </article>
          </el-tooltip>
        </div>
        <el-empty v-else :description="`暂无${z.title}`" :image-size="50" />
      </section>
    </div>

    <!-- 项目详情抽屉 -->
    <ProjectDetailDrawer
      v-model:visible="detailVisible"
      :project="detailProject"
      @updated="onDetailUpdated"
    />

    <!-- 立即催办弹窗（与催办设置复用同一组件） -->
    <ManualFollowupDialog v-model="manualFollowupVisible" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Grid, List, Bell } from '@element-plus/icons-vue'
import { projectApi, userApi, departmentApi } from '@/api/resources'
import type { Project, ProjectStatus, ProjectUrgency, User, Department } from '@/types'
import {
  projectStatusLabel, projectStatusColor, urgencyLabel, urgencyColor, isOverdue, progressStatusColor,
  PENDING_STATUSES, completionGradient,
} from '@/utils/labels'
import BaseChart from '@/components/BaseChart.vue'
import ProjectDetailDrawer from '@/components/ProjectDetailDrawer.vue'
import ManualFollowupDialog from '@/components/ManualFollowupDialog.vue'
import { useAuthStore } from '@/stores/auth'
import { useBrandingStore } from '@/stores/branding'

const allProjects = ref<Project[]>([])
const loading = ref(false)
const viewMode = ref<'grid' | 'list'>('grid')

/* 立即催办弹窗（仅管理员可见入口） */
const manualFollowupVisible = ref(false)

/* 首页副标题动态统计：部门数 / 项目经理(含管理员)数 / 最新登录用户 */
const users = ref<User[]>([])
const departments = ref<Department[]>([])
const auth = useAuthStore()
const isAdmin = computed(() => auth.currentUser?.role === 'admin')
const branding = useBrandingStore()
const subtitle = computed(() => {
  const deptCount = departments.value.length
  const managerCount = users.value.filter(
    (u) => u.role === 'project_manager' || u.role === 'admin',
  ).length
  // 最近活跃用户排除当前登录者自己（否则自己登录后看到的「最近活跃」永远是自己）
  const meId = auth.currentUser?.id
  const withLogin = users.value.filter((u) => u.last_login_at && u.id !== meId)
  let who = '—'
  if (withLogin.length) {
    const latest = withLogin.reduce((a, b) =>
      (a.last_login_at || '') > (b.last_login_at || '') ? a : b)
    who = `${latest.name}（${fmtLoginTime(latest.last_login_at)}）`
  }
  const scope = branding.data.org_scope || '全公司'
  const unit = branding.data.dept_unit || '部门'
  return `目前本系统管理涵盖${scope} ${deptCount} 个${unit}，${managerCount} 位项目经理，最近活跃的用户是 ${who}。`
})

/* 格式化最后活跃时间：后端存 UTC（无时区后缀），按 UTC 解析后转北京时间显示，避免差 8 小时 */
function fmtLoginTime(s?: string | null): string {
  if (!s) return '—'
  // 无时区后缀的字符串按 UTC 处理（补 Z），否则 JS 会当本地时区解析导致偏差
  const iso = /[zZ]|[+-]\d\d:?\d\d$/.test(s) ? s : s + 'Z'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return s.replace('T', ' ').slice(0, 16)
  return d.toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai', hour12: false,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

/* 详情抽屉 */
const detailVisible = ref(false)
const detailProject = ref<Project | null>(null)
function openDetail(row: Project) {
  detailProject.value = row
  detailVisible.value = true
}
function onDetailUpdated() {
  loadProjects()
}

const statusLabel = (s: ProjectStatus) => projectStatusLabel[s]
const statusColor = (s: ProjectStatus) => projectStatusColor[s]
const urgencyText = (u: ProjectUrgency) => urgencyLabel[u]
const urgColor = (u: ProjectUrgency) => urgencyColor[u]
const overdue = (p: Project) => isOverdue(p.estimated_end_date, p.status)
const progressColor = (s?: string | null) => (s && progressStatusColor[s]) || 'var(--c-ink-3)'

/* 项目是否存在「未闭合」的待讨论/待确认/待执行进展
   （pending 状态、非反馈本身、且其 id 未被任何 reply_to 引用） */
function hasUnclosedPending(p: Project): boolean {
  const log = p.progress_log ?? []
  const replied = new Set(log.filter((e) => e.reply_to).map((e) => e.reply_to))
  return log.some((e) =>
    (PENDING_STATUSES as readonly string[]).includes(e.status)
    && !e.reply_to
    && !(e.id && replied.has(e.id)),
  )
}

/* ---------- 首页滚动信息流 ---------- */
type FeedItem = {
  projectId: number
  projectName: string
  ownerName: string
  time: string
  status: string
  content: string
}

// 截断到 64 字符，超出以省略号代替
function truncate(s: string, n = 64): string {
  const t = (s || '').trim()
  return t.length > n ? t.slice(0, n) + '……' : t
}

// 最新进展：所有项目所有带时间的进展条目，按 time 倒序取最新 30 条
const latestFeed = computed<FeedItem[]>(() => {
  const items: FeedItem[] = []
  for (const p of allProjects.value) {
    for (const e of (p.progress_log ?? [])) {
      if (!e.time) continue
      items.push({
        projectId: p.id, projectName: p.name, ownerName: p.owner_name || '—',
        time: e.time, status: e.status, content: truncate(e.content),
      })
    }
  }
  return items.sort((a, b) => b.time.localeCompare(a.time)).slice(0, 30)
})

// 待处理：未闭合 pending 条目（status∈PENDING、无 reply_to、id 未被任何 reply_to 引用），按 time 倒序取 30
const pendingFeed = computed<FeedItem[]>(() => {
  const items: FeedItem[] = []
  for (const p of allProjects.value) {
    const log = p.progress_log ?? []
    const replied = new Set(log.filter((e) => e.reply_to).map((e) => e.reply_to))
    for (const e of log) {
      if (!e.time) continue
      if (!(PENDING_STATUSES as readonly string[]).includes(e.status)) continue
      if (e.reply_to) continue
      if (e.id && replied.has(e.id)) continue
      items.push({
        projectId: p.id, projectName: p.name, ownerName: p.owner_name || '—',
        time: e.time, status: e.status, content: truncate(e.content),
      })
    }
  }
  return items.sort((a, b) => b.time.localeCompare(a.time)).slice(0, 30)
})

// 点击信息条 → 按 projectId 找回 Project 并打开详情
function openFeedItem(it: FeedItem) {
  const p = allProjects.value.find((x) => x.id === it.projectId)
  if (p) openDetail(p)
}

/* 信息看板统计（全部基于 allProjects 计算） */
const boardStats = computed(() => {
  const ps = allProjects.value
  const inProgressList = ps.filter((p) => p.status === 'in_progress')
  // 待执行项目：非已完成/取消，且存在未闭合的待讨论/待确认/待执行
  const pending = ps
    .filter((p) => !['completed', 'cancelled'].includes(p.status))
    .filter(hasUnclosedPending).length
  // 反馈及时度：进行中且无未闭合 pending 的项目 / 进行中项目
  const timely = inProgressList.filter((p) => !hasUnclosedPending(p)).length
  const timeliness = inProgressList.length ? Math.round((timely / inProgressList.length) * 100) : 0
  return {
    total: ps.length,
    inProgress: inProgressList.length,
    completed: ps.filter((p) => p.status === 'completed').length,
    pending,
    timeliness,
  }
})

const timelinessColor = computed(() => {
  const v = boardStats.value.timeliness
  return v >= 80 ? '#3DBE7B' : v >= 50 ? '#E6A23C' : '#E5484D'
})

const timelinessGauge = computed(() => ({
  series: [{
    type: 'gauge',
    radius: '135%',
    center: ['50%', '85%'],
    startAngle: 200,
    endAngle: -20,
    min: 0,
    max: 100,
    splitNumber: 5,
    axisLine: { lineStyle: { width: 4, color: [[0.5, '#E5484D'], [0.8, '#E6A23C'], [1, '#3DBE7B']] } },
    axisTick: { distance: -4, length: 3, lineStyle: { color: '#fff', width: 1 } },
    splitLine: { distance: -4, length: 6, lineStyle: { color: '#fff', width: 1.5 } },
    axisLabel: { show: false },
    pointer: { show: true, length: '62%', width: 3, itemStyle: { color: timelinessColor.value } },
    anchor: { show: true, size: 6, itemStyle: { color: timelinessColor.value } },
    detail: { show: false },
    data: [{ value: boardStats.value.timeliness }],
  }],
} as Record<string, unknown>))

/* 三个关注分区（仅展示进行中项目；项目可同时出现在多个区）。
   边缘色：
   - 重点：重要=深红 #C0392B、高=浅红 #EF8A8A
   - 等待关注：按最新进展状态着色（待确认=粉、待讨论=橙、待执行=青）
   - 延迟关注：按最新进展状态着色（阻塞=红、延迟=黄），阻塞优先 */
const zones = computed(() => {
  const active = allProjects.value
    .filter((p) => p.status === 'in_progress')
    .map((p) => {
      const log = [...(p.progress_log ?? [])].sort((a, b) => (a.time || '').localeCompare(b.time || ''))
      return {
        ...p,
        _latest: log.length ? log[log.length - 1] : null,
        _recent: log.slice(-8),
        _hasMore: log.length > 8,
      }
    })
  // 重点项目：重要(urgent) 在前，高(high) 在后
  const key = [
    ...active.filter((p) => p.urgency === 'urgent'),
    ...active.filter((p) => p.urgency === 'high'),
  ]
  const wait = active.filter((p) => ['待讨论', '待确认', '待执行'].includes(p._latest?.status || ''))
  // 延迟关注：纳入阻塞与延迟，阻塞优先排在延迟之前
  const delay = [
    ...active.filter((p) => (p._latest?.status || '') === '阻塞'),
    ...active.filter((p) => (p._latest?.status || '') === '延迟'),
  ]
  return [
    { key: 'key', title: '重点项目', desc: '优先级：重要 / 高', items: key, barColor: (p: Project) => urgencyColor[p.urgency] },
    { key: 'wait', title: '待处理事件', desc: '最新进展：待讨论 / 待确认 / 待执行', items: wait, barColor: (p: Project & { _latest?: { status?: string } | null }) => progressColor(p._latest?.status) },
    { key: 'delay', title: '延迟关注', desc: '最新进展：阻塞 / 延迟', items: delay, barColor: (p: Project & { _latest?: { status?: string } | null }) => progressColor(p._latest?.status) },
  ]
})

// 解析 CSS 变量为实际色值（ECharts 不识别 var()）
function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || '#999'
}

const deptOption = computed(() => {
  const counts: Record<string, number> = {}
  for (const p of allProjects.value) {
    // 排除已完成/已取消项目，只统计在跟踪的项目
    if (['completed', 'cancelled'].includes(p.status)) continue
    const key = p.department || '未分配'
    counts[key] = (counts[key] || 0) + 1
  }
  const data = Object.entries(counts)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['40%', '62%'],
      avoidLabelOverlap: true,
      label: { show: true, formatter: '{b}: {c}', color: cssVar('--c-ink-2'), fontSize: 12 },
      labelLine: { show: true, length: 10, length2: 12 },
      data: data.length ? data : [{ name: '暂无', value: 1, itemStyle: { color: cssVar('--c-border') } }],
    }],
  } as Record<string, unknown>
})

const ownerOption = computed(() => {
  const counts: Record<string, number> = {}
  for (const p of allProjects.value) {
    // 排除已完成/已取消项目，只统计在跟踪的项目
    if (['completed', 'cancelled'].includes(p.status)) continue
    const key = p.owner_name || '未分配'
    counts[key] = (counts[key] || 0) + 1
  }
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1])
  // 统一冷色系调色板（蓝/青/靛/青绿），按柱循环
  const coolPalette = ['#1A73E8', '#2F8FE0', '#13C2C2', '#3B6FE0', '#5AB1BB', '#2F54EB', '#41B0D8', '#6979F8']
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 8, right: 16, top: 16, bottom: 8, containLabel: true },
    xAxis: {
      type: 'category',
      data: entries.map(([name]) => name),
      axisLine: { lineStyle: { color: cssVar('--c-border-strong') } },
      axisLabel: { color: cssVar('--c-ink-2'), interval: 0, rotate: entries.length > 6 ? 35 : 0 },
    },
    yAxis: {
      type: 'value', minInterval: 1,
      splitLine: { lineStyle: { color: cssVar('--c-border') } },
      axisLabel: { color: cssVar('--c-ink-3') },
    },
    series: [{
      type: 'bar',
      barWidth: '46%',
      data: entries.map(([, value], i) => ({
        value,
        itemStyle: { color: coolPalette[i % coolPalette.length], borderRadius: [4, 4, 0, 0] },
      })),
    }],
  } as Record<string, unknown>
})

async function loadProjects() {
  loading.value = true
  try {
    allProjects.value = await projectApi.list({ limit: 500 })
  } catch {
    ElMessage.error('加载项目失败')
  } finally {
    loading.value = false
  }
}

async function loadMeta() {
  try {
    const [us, ds] = await Promise.all([
      userApi.list({ limit: 200 }),
      departmentApi.list({ limit: 100 }),
    ])
    users.value = us
    departments.value = ds
  } catch {
    // 副标题统计为可选增强，失败时优雅降级
  }
}

onMounted(() => {
  loadProjects()
  loadMeta()
})
</script>

<style scoped>
.stats {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--sp-4);
  margin-bottom: var(--sp-5);
}
@media (max-width: 900px) { .stats { grid-template-columns: repeat(2, 1fr); } }
.stat-card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  padding: var(--sp-4) var(--sp-5);
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  box-shadow: var(--shadow-sm);
}
.stat-label { color: var(--c-ink-3); font-size: 13px; font-weight: 500; }
.stat-num { font-size: 30px; font-weight: 700; line-height: 1; }
/* 反馈及时度卡片：左侧标签+数字（决定卡片高度，与其他卡一致），右侧紧凑环形仪表盘 */
.gauge-card { flex-direction: row; align-items: center; justify-content: space-between; gap: var(--sp-2); }
.gauge-left { display: flex; flex-direction: column; gap: var(--sp-2); min-width: 0; }
.gauge-box { width: 76px; flex-shrink: 0; }

.charts {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: var(--sp-4);
  margin-bottom: var(--sp-5);
}
@media (max-width: 720px) { .charts { grid-template-columns: 1fr; } }
.chart-card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  padding: var(--sp-4) var(--sp-5);
  box-shadow: var(--shadow-sm);
}
.chart-title { font-size: 14px; font-weight: 600; margin-bottom: var(--sp-2); color: var(--c-ink-2); }

/* 滚动信息流 */
.feeds {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sp-4);
  margin-bottom: var(--sp-5);
}
@media (max-width: 900px) { .feeds { grid-template-columns: 1fr; } }
.feed {
  min-width: 0;   /* 关键：防止 nowrap 长文本撑宽 grid 列，确保两区严格各占 50%、与图表区对齐 */
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  padding: var(--sp-3) var(--sp-4);
  box-shadow: var(--shadow-sm);
}
.feed-latest { background: #EAF2FE; }   /* 淡蓝 */
.feed-pending { background: #E6F7F7; }   /* 淡青 */
.feed-title { font-size: 14px; font-weight: 600; margin-bottom: var(--sp-2); color: var(--c-ink-2); }
.feed-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--sp-2); }
.feed-head .feed-title { margin-bottom: 0; }
.feed-viewport { height: 200px; overflow: hidden; position: relative; }
.feed-track {
  margin: 0; padding: 0; list-style: none;
  display: flex; flex-direction: column; gap: 4px;
  animation: feed-scroll 60s linear infinite;
}
.feed-viewport:hover .feed-track { animation-play-state: paused; }
@keyframes feed-scroll {
  from { transform: translateY(0); }
  to { transform: translateY(-50%); }
}
.feed-row {
  display: flex; align-items: flex-start; gap: 6px;
  font-size: 13px; line-height: 1.6;
  cursor: pointer; padding: 2px 4px; border-radius: var(--r-sm);
}
.feed-row:hover { background: rgba(255, 255, 255, 0.6); }
.fr-proj { font-weight: 600; color: var(--c-ink); flex-shrink: 0; white-space: nowrap; }
/* 中列：日期+状态+内容；内容过长在此换行，续行自动对齐到日期首字（中列左边缘） */
.fr-main { flex: 1; min-width: 0; }
.fr-date { color: var(--c-ink-3); margin-right: 6px; }
.fr-status { font-weight: 600; margin-right: 6px; }
.fr-content { color: var(--c-ink-2); }
.fr-owner { color: var(--c-ink-3); flex-shrink: 0; white-space: nowrap; }
.feed-empty { height: 200px; display: grid; place-items: center; font-size: 13px; }

/* 关注分区 */
.zones { display: flex; flex-direction: column; gap: var(--sp-5); }
.zone { border-top: 1px solid var(--c-border); padding-top: var(--sp-4); }
.zone-head { display: flex; align-items: center; gap: var(--sp-3); margin-bottom: var(--sp-3); }
.zone-switch { margin-left: auto; }
.zone-title { font-size: 16px; font-weight: 700; display: flex; align-items: center; gap: var(--sp-2); position: relative; }
/* 重点项目标题下方衬托半透明渐变红（右深左浅），不挡文字 */
.zone-key .zone-title::after,
.zone-wait .zone-title::after,
.zone-delay .zone-title::after {
  content: '';
  position: absolute;
  left: -6px; right: -6px; bottom: -3px;
  height: 9px;
  border-radius: 999px;
  z-index: -1;
  pointer-events: none;
}
/* 左浓右淡，三色：重点=红 / 待处理事件=粉 / 延迟关注=琥珀 */
.zone-key .zone-title::after { background: linear-gradient(90deg, rgba(192, 57, 43, 0.28) 0%, rgba(192, 57, 43, 0) 100%); }
.zone-wait .zone-title::after { background: linear-gradient(90deg, rgba(232, 127, 176, 0.32) 0%, rgba(232, 127, 176, 0) 100%); }
.zone-delay .zone-title::after { background: linear-gradient(90deg, rgba(230, 162, 60, 0.32) 0%, rgba(230, 162, 60, 0) 100%); }
.zone-count {
  font-size: 13px; font-weight: 600; color: var(--c-accent);
  background: var(--c-accent-soft); padding: 1px 9px; border-radius: 999px;
}
.zone-desc { font-size: 12px; }
.pc-latest {
  font-size: 13px; color: var(--c-ink-2); line-height: 1.5; margin-top: var(--sp-2);
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
}
.pc-latest-status { font-weight: 600; }

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--sp-4);
  gap: var(--sp-4);
  flex-wrap: wrap;
}
.filters { display: flex; gap: var(--sp-3); flex-wrap: wrap; }

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--sp-3);
}
.list { display: flex; flex-direction: column; gap: var(--sp-2); }

.project-card {
  position: relative;
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-left: 4px solid var(--bar);
  border-radius: var(--r-md);
  padding: var(--sp-3) var(--sp-4);
  cursor: pointer;
  transition: box-shadow 0.15s, transform 0.1s, border-color 0.15s;
}
.project-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.list .project-card { display: grid; grid-template-columns: 1.5fr 1.2fr 1fr 2fr; align-items: center; gap: var(--sp-4); }
.list .pc-top, .list .pc-meta, .list .pc-progress, .list .pc-latest { margin: 0; }
.list .pc-latest { -webkit-line-clamp: 2; }

.pc-top { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--sp-2); margin-bottom: var(--sp-2); }
.pc-name { font-size: 15px; flex: 1; min-width: 0; }
.pc-top-tags { display: flex; align-items: center; gap: var(--sp-2); flex-shrink: 0; }
.pc-status { font-weight: 600; font-size: 12px; white-space: nowrap; }
.overdue-tag {
  font-size: 11px; font-weight: 600;
  color: var(--c-status-overdue);
  background: var(--c-status-overdue-soft);
  padding: 2px 8px; border-radius: 999px;
}
.pc-meta { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; font-size: 13px; margin-bottom: var(--sp-3); }
.badge { font-weight: 600; font-size: 12px; padding: 2px 8px; border-radius: var(--r-sm); }

.pc-progress { display: flex; align-items: center; gap: var(--sp-3); }
.bar { flex: 1; height: 6px; background: var(--c-canvas); border-radius: 999px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 999px; transition: width 0.3s; }
.pc-pct { font-size: 13px; font-weight: 600; color: var(--c-ink-2); min-width: 38px; text-align: right; }
.pc-longterm { font-size: 13px; font-weight: 700; color: var(--c-accent); }
</style>

<!-- 「项目进展」tooltip 样式（teleport 到 body，需全局） -->
<style>
.el-popper.progress-tip.is-light {
  max-width: 480px;
  background: #f5ecd9;
  color: #1a1a1a;
  border-color: #e0d3b8;
  padding: 8px 12px;
}
.el-popper.progress-tip .ptip-more { text-align: center; color: #8a7a55; font-weight: 700; line-height: 1; margin-bottom: 6px; }
.el-popper.progress-tip .ptip-item { display: flex; gap: 10px; padding: 4px 0; line-height: 1.5; border-top: 1px dashed #e0d3b8; }
.el-popper.progress-tip .ptip-item:first-of-type { border-top: none; }
.el-popper.progress-tip .ptip-time { color: #8a7a55; font-size: 12px; white-space: nowrap; flex-shrink: 0; }
.el-popper.progress-tip .ptip-text { word-break: break-word; white-space: normal; }
.el-popper.progress-tip .ptip-meeting { color: #1a73e8; font-weight: 700; }
.el-popper.progress-tip .el-popper__arrow::before { background: #f5ecd9; border-color: #e0d3b8; }
</style>
