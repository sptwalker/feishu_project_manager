<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">项目看板</h1>
        <p class="muted">掌握所有项目的进度与风险</p>
      </div>
      <div class="head-actions">
        <el-button :icon="Upload" :loading="importing" @click="triggerImport">表格导入</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">新建项目</el-button>
        <input ref="fileInput" type="file" accept=".xlsx" style="display:none" @change="onFileChosen" />
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats">
      <div class="stat-card">
        <span class="stat-label">项目总数</span>
        <span class="stat-num num">{{ stats?.projects.total ?? '–' }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">进行中</span>
        <span class="stat-num num" style="color: var(--c-status-progress)">
          {{ stats?.projects.by_status?.in_progress ?? '–' }}
        </span>
      </div>
      <div class="stat-card">
        <span class="stat-label">逾期</span>
        <span class="stat-num num" style="color: var(--c-status-overdue)">
          {{ stats?.projects.overdue ?? '–' }}
        </span>
      </div>
      <div class="stat-card">
        <span class="stat-label">平均完成度</span>
        <span class="stat-num num">{{ stats ? stats.projects.avg_completion + '%' : '–' }}</span>
      </div>
    </div>

    <!-- 可视化图表 -->
    <div v-if="allProjects.length" class="charts">
      <div class="chart-card">
        <h3 class="chart-title">部门项目数量</h3>
        <BaseChart :option="deptOption" :height="220" />
      </div>
      <div class="chart-card">
        <h3 class="chart-title">负责人项目数量</h3>
        <BaseChart :option="ownerOption" :height="220" />
      </div>
    </div>

    <!-- 筛选 + 视图切换 -->
    <div class="toolbar">
      <div class="filters">
        <el-select v-model="filterStatus" placeholder="全部状态" clearable size="default" style="width: 140px" @change="load">
          <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
        <el-input v-model="keyword" placeholder="搜索项目名称" clearable :prefix-icon="Search" style="width: 220px" />
      </div>
      <el-radio-group v-model="viewMode" size="default">
        <el-radio-button value="grid"><el-icon><Grid /></el-icon></el-radio-button>
        <el-radio-button value="list"><el-icon><List /></el-icon></el-radio-button>
      </el-radio-group>
    </div>

    <!-- 列表/网格 -->
    <div v-loading="loading">
      <el-empty v-if="!loading && filtered.length === 0" description="暂无项目" />

      <div v-else :class="viewMode === 'grid' ? 'grid' : 'list'">
        <article
          v-for="p in filtered"
          :key="p.id"
          class="project-card"
          :style="{ '--bar': statusColor(p.status) }"
          @click="goTasks(p.id)"
        >
          <div class="pc-top">
            <h3 class="pc-name">{{ p.name }}</h3>
            <span v-if="overdue(p)" class="overdue-tag">逾期</span>
          </div>
          <div class="pc-meta">
            <span class="badge" :style="{ color: statusColor(p.status), background: 'var(--c-surface-2)' }">
              {{ statusLabel(p.status) }}
            </span>
            <span class="muted">· {{ urgencyText(p.urgency) }}</span>
            <span v-if="p.department" class="muted">· {{ p.department }}</span>
          </div>
          <div class="pc-progress">
            <div class="bar"><div class="bar-fill" :style="{ width: p.completion + '%', background: statusColor(p.status) }" /></div>
            <span class="num pc-pct">{{ p.completion }}%</span>
          </div>
          <div class="pc-foot muted">
            <span>预计 {{ p.estimated_end_date || '—' }}</span>
          </div>
        </article>
      </div>
    </div>

    <!-- 新建项目对话框 -->
    <el-dialog v-model="createVisible" title="新建项目" width="480px">
      <el-form :model="form" label-width="92px" label-position="left">
        <el-form-item label="项目名称" required>
          <el-input v-model="form.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="记录日期" required>
          <el-date-picker v-model="form.record_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="负责人">
          <el-input v-model="form.owner_name" placeholder="负责人姓名（可选）" style="width: 100%" />
        </el-form-item>
        <el-form-item label="紧急程度">
          <el-select v-model="form.urgency" style="width: 100%">
            <el-option v-for="u in urgencyOptions" :key="u.value" :label="u.label" :value="u.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="form.department" placeholder="可选" />
        </el-form-item>
        <el-form-item label="预计完成">
          <el-date-picker v-model="form.estimated_end_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Search, Grid, List, Upload } from '@element-plus/icons-vue'
import { projectApi, statsApi } from '@/api/resources'
import type { Project, ProjectStatus, ProjectUrgency, DashboardStats } from '@/types'
import {
  projectStatusLabel, projectStatusColor, urgencyLabel, isOverdue,
} from '@/utils/labels'
import BaseChart from '@/components/BaseChart.vue'

const router = useRouter()

const projects = ref<Project[]>([])
const allProjects = ref<Project[]>([])
const stats = ref<DashboardStats | null>(null)
const loading = ref(false)
const viewMode = ref<'grid' | 'list'>('grid')
const filterStatus = ref<ProjectStatus | ''>('')
const keyword = ref('')

const statusOptions = [
  { value: 'planned', label: '待启动' },
  { value: 'in_progress', label: '进行中' },
  { value: 'paused', label: '暂停' },
  { value: 'completed', label: '已完成' },
  { value: 'cancelled', label: '已取消' },
]
const urgencyOptions = [
  { value: 'low', label: '低' },
  { value: 'medium', label: '中' },
  { value: 'high', label: '高' },
  { value: 'urgent', label: '紧急' },
]

const statusLabel = (s: ProjectStatus) => projectStatusLabel[s]
const statusColor = (s: ProjectStatus) => projectStatusColor[s]
const urgencyText = (u: ProjectUrgency) => urgencyLabel[u]
const overdue = (p: Project) => isOverdue(p.estimated_end_date, p.status)

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return projects.value.filter((p) => !kw || p.name.toLowerCase().includes(kw))
})

// 解析 CSS 变量为实际色值（ECharts 不识别 var()）
function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || '#999'
}

const deptOption = computed(() => {
  const counts: Record<string, number> = {}
  for (const p of allProjects.value) {
    const key = p.department || '未分配'
    counts[key] = (counts[key] || 0) + 1
  }
  const data = Object.entries(counts)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, icon: 'circle', type: 'scroll', textStyle: { color: cssVar('--c-ink-2') } },
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      avoidLabelOverlap: true,
      label: { show: false },
      data: data.length ? data : [{ name: '暂无', value: 1, itemStyle: { color: cssVar('--c-border') } }],
    }],
  } as Record<string, unknown>
})

const ownerOption = computed(() => {
  const counts: Record<string, number> = {}
  for (const p of allProjects.value) {
    const key = p.owner_name || '未分配'
    counts[key] = (counts[key] || 0) + 1
  }
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1])
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
      data: entries.map(([, value]) => ({
        value,
        itemStyle: { color: cssVar('--c-accent'), borderRadius: [4, 4, 0, 0] },
      })),
    }],
  } as Record<string, unknown>
})

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { limit: 100 }
    if (filterStatus.value) params.status = filterStatus.value
    projects.value = await projectApi.list(params)
  } catch {
    ElMessage.error('加载项目失败')
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    stats.value = await statsApi.dashboard()
  } catch {
    /* 统计失败不阻塞页面 */
  }
}

async function loadCharts() {
  try {
    allProjects.value = await projectApi.list({ limit: 500 })
  } catch {
    /* 图表统计失败不阻塞页面 */
  }
}

function goTasks(id: number) {
  router.push({ name: 'project-tasks', params: { id } })
}

/* 表格导入 */
const fileInput = ref<HTMLInputElement | null>(null)
const importing = ref(false)

function triggerImport() {
  fileInput.value?.click()
}

async function onFileChosen(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''  // 允许重复选择同一文件
  if (!file) return
  importing.value = true
  try {
    const res = await projectApi.importExcel(file)
    if (res.error_count > 0) {
      ElMessage.warning(`导入完成：成功 ${res.created} 条，失败 ${res.error_count} 条`)
    } else {
      ElMessage.success(`导入成功 ${res.created} 条项目`)
    }
    await Promise.all([load(), loadStats(), loadCharts()])
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail ? `导入失败：${detail}` : '导入失败，请检查表格格式')
  } finally {
    importing.value = false
  }
}

/* 新建项目 */
const createVisible = ref(false)
const saving = ref(false)
const form = reactive<Record<string, unknown>>({
  name: '', record_date: '', owner_name: '', urgency: 'medium', department: '', estimated_end_date: null,
})

function openCreate() {
  Object.assign(form, {
    name: '', record_date: new Date().toISOString().slice(0, 10),
    owner_name: '', urgency: 'medium', department: '', estimated_end_date: null,
  })
  createVisible.value = true
}

async function submitCreate() {
  if (!form.name || !form.record_date) {
    ElMessage.warning('请填写必填项')
    return
  }
  saving.value = true
  try {
    const payload: Record<string, unknown> = { ...form }
    if (!payload.department) delete payload.department
    if (!payload.owner_name) delete payload.owner_name
    if (!payload.estimated_end_date) delete payload.estimated_end_date
    await projectApi.create(payload as Partial<Project>)
    ElMessage.success('项目已创建')
    createVisible.value = false
    await Promise.all([load(), loadStats(), loadCharts()])
  } catch {
    ElMessage.error('创建失败（需要管理员或项目经理权限）')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  load()
  loadStats()
  loadCharts()
})
</script>

<style scoped>
.head-actions { display: flex; gap: var(--sp-2); align-items: center; }
.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--sp-4);
  margin-bottom: var(--sp-5);
}
@media (max-width: 720px) { .stats { grid-template-columns: repeat(2, 1fr); } }
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
  grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
  gap: var(--sp-4);
}
.list { display: flex; flex-direction: column; gap: var(--sp-3); }

.project-card {
  position: relative;
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-left: 3px solid var(--bar);
  border-radius: var(--r-md);
  padding: var(--sp-4) var(--sp-5);
  cursor: pointer;
  transition: box-shadow 0.15s, transform 0.1s, border-color 0.15s;
}
.project-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.list .project-card { display: grid; grid-template-columns: 2fr 1.2fr 1.4fr 1fr; align-items: center; gap: var(--sp-4); }
.list .pc-progress { margin: 0; }
.list .pc-foot { margin: 0; }

.pc-top { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-2); margin-bottom: var(--sp-2); }
.pc-name { font-size: 16px; }
.overdue-tag {
  font-size: 11px; font-weight: 600;
  color: var(--c-status-overdue);
  background: var(--c-status-overdue-soft);
  padding: 2px 8px; border-radius: 999px;
}
.pc-meta { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; font-size: 13px; margin-bottom: var(--sp-4); }
.badge { font-weight: 600; font-size: 12px; padding: 2px 8px; border-radius: var(--r-sm); }

.pc-progress { display: flex; align-items: center; gap: var(--sp-3); margin-bottom: var(--sp-3); }
.bar { flex: 1; height: 6px; background: var(--c-canvas); border-radius: 999px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 999px; transition: width 0.3s; }
.pc-pct { font-size: 13px; font-weight: 600; color: var(--c-ink-2); min-width: 38px; text-align: right; }
.pc-foot { font-size: 12px; }
</style>
