<template>
  <div class="page">
    <div class="page-head">
      <h1 class="page-title">项目总览</h1>
    </div>

    <div class="head-toolbar">
      <p class="muted">目前有 {{ trackingCount }} 个跟踪项目（除去已完成/取消/暂停），其中重要项目 {{ importantCount }} 个</p>
      <div class="head-actions">
        <el-input
          v-model="keyword" placeholder="搜索项目名称" clearable
          :prefix-icon="Search" style="width: 220px"
        />
        <el-button text :icon="View" :disabled="!currentRow" @click="detailSelected">详情</el-button>
        <el-button text type="danger" :icon="Delete" :disabled="!currentRow" @click="removeSelected">删除</el-button>
        <el-button text :icon="Plus" @click="openCreate">新增项目</el-button>
      </div>
    </div>

    <el-table
      v-loading="loading"
      :data="rows"
      stripe
      border
      size="default"
      row-key="id"
      highlight-current-row
      :header-cell-style="headerCellStyle"
      :default-sort="{ prop: '', order: null }"
      style="width: 100%"
      @current-change="onCurrentChange"
      @row-dblclick="openDetail"
    >
      <el-table-column
        prop="department" label="部门" width="130"
        sortable :sort-method="sortDept"
        :filters="deptFilters" :filter-method="filterDept"
      >
        <template #default="{ row }">
          <span :style="{ color: row._deptColor, fontWeight: row._deptShort ? 600 : 400 }">
            {{ row._deptShort || '—' }}
          </span>
        </template>
      </el-table-column>

      <el-table-column
        prop="status" label="完成情况" width="130"
        sortable :sort-method="cmpStatus"
        :filters="statusFilters" :filter-method="filterStatus"
        :filtered-value="defaultStatusFiltered"
      >
        <template #default="{ row }">
          <span class="badge" :style="{ color: statusColor(row.status), background: 'var(--c-surface-2)' }">
            {{ statusLabel(row.status) }}
          </span>
        </template>
      </el-table-column>

      <el-table-column prop="name" label="待办事项 / 项目名称" min-width="240">
        <template #default="{ row }">
          <el-tooltip
            v-if="row.content"
            :content="row.content"
            placement="top" effect="light" popper-class="desc-tip"
          >
            <span class="link" @click="openDetail(row)">{{ row.name }}</span>
          </el-tooltip>
          <span v-else class="link" @click="openDetail(row)">{{ row.name }}</span>
        </template>
      </el-table-column>

      <el-table-column
        label="项目进展" min-width="320"
        :filters="progressFilters" :filter-method="filterProgress"
      >
        <template #default="{ row }">
          <el-tooltip
            v-if="row._recentProgress.length"
            placement="bottom" effect="light" popper-class="progress-tip"
          >
            <template #content>
              <div class="ptip">
                <div v-if="row._hasMore" class="ptip-more">……</div>
                <div v-for="(e, i) in row._recentProgress" :key="i" class="ptip-item">
                  <span class="ptip-time">{{ e.time || '—' }}</span>
                  <span class="ptip-text"><span v-if="e.meeting_session" class="ptip-meeting">【第{{ e.meeting_session }}次周会更新】</span>{{ e.content }}</span>
                </div>
              </div>
            </template>
            <span class="progress-cell"><span v-if="row._lastStatus" class="prog-status" :style="{ color: progressColor(row._lastStatus) }">【{{ row._lastStatus }}】</span>{{ row._lastProgress || '—' }}</span>
          </el-tooltip>
          <span v-else>—</span>
        </template>
      </el-table-column>

      <el-table-column
        prop="owner_name" label="负责人" width="130"
        sortable :sort-method="sortOwner"
        :filters="ownerFilters" :filter-method="filterOwner"
      >
        <template #default="{ row }">{{ row.owner_name || '—' }}</template>
      </el-table-column>

      <el-table-column
        prop="urgency" label="优先级" width="110"
        sortable :sort-method="sortUrgency"
        :filters="urgencyFilters" :filter-method="filterUrgency"
      >
        <template #default="{ row }">
          <span class="urg" :style="{ color: urgColor(row.urgency) }">{{ urgText(row.urgency) }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="completion" label="进度" width="150" sortable>
        <template #default="{ row }">
          <span v-if="row.is_long_term" class="long-term-text">长期项目</span>
          <template v-else>
            <div class="tbar"><div class="tbar-fill" :style="{ width: row.completion + '%', background: statusColor(row.status) }" /></div>
            <span class="num tpct">{{ row.completion }}%</span>
          </template>
        </template>
      </el-table-column>

      <el-table-column prop="record_date" label="记录日期" width="128" sortable>
        <template #default="{ row }">{{ row.record_date || '—' }}</template>
      </el-table-column>

      <el-table-column prop="estimated_end_date" label="截止日期" width="128" sortable>
        <template #default="{ row }">
          <span :class="{ overdue: isOverdue(row.estimated_end_date, row.status) }">
            {{ row.estimated_end_date || '—' }}
          </span>
        </template>
      </el-table-column>

      <template #empty>
        <el-empty description="暂无项目，点击右上角「新增项目」或导入 Excel" />
      </template>
    </el-table>

    <div class="footer-bar muted">
      共 {{ rows.length }} 个项目 · {{ currentRow ? '已选中：' + currentRow.name : '单击选中行，双击查看详情' }}
    </div>

    <!-- 详情抽屉（兼新建项目） -->
    <ProjectDetailDrawer
      v-model:visible="detailVisible"
      :project="detailProject"
      :create-mode="createMode"
      :departments="deptValues"
      :owners="ownerValues"
      @updated="load"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, View, Delete } from '@element-plus/icons-vue'
import { projectApi, departmentApi } from '@/api/resources'
import type { Project, ProjectStatus, ProjectUrgency, Department } from '@/types'
import {
  projectStatusLabel, projectStatusColor, urgencyLabel, urgencyColor,
  urgencyWeight, PROJECT_STATUS_ORDER, PROGRESS_STATUSES, isOverdue, progressStatusColor,
} from '@/utils/labels'
import ProjectDetailDrawer from '@/components/ProjectDetailDrawer.vue'

const projects = ref<Project[]>([])
const departments = ref<Department[]>([])
const loading = ref(false)
const keyword = ref('')

const statusLabel = (s: ProjectStatus) => projectStatusLabel[s]
const statusColor = (s: ProjectStatus) => projectStatusColor[s]
const urgText = (u: ProjectUrgency) => urgencyLabel[u]
const urgColor = (u: ProjectUrgency) => urgencyColor[u]
const urgWeight = (u: ProjectUrgency) => urgencyWeight[u] ?? 0
const progressColor = (s?: string) => (s && progressStatusColor[s]) || 'var(--c-ink-3)'

/* 按全称或简称匹配部门记录（项目的 department 字段历史上混存了全称/简称/变体） */
function findDepartment(deptName?: string | null) {
  if (!deptName) return undefined
  const key = deptName.trim()
  return departments.value.find(d => d.name === key || d.short_name === key)
}

/* 获取部门颜色 */
function getDepartmentColor(deptName?: string | null) {
  return findDepartment(deptName)?.color || undefined
}

/* 获取部门简称（映射为部门表中的简称；无对应部门则暂空） */
function getDepartmentShortName(deptName?: string | null) {
  return findDepartment(deptName)?.short_name || ''
}

/* 表头：文字居中 + 黑色 */
const headerCellStyle = { textAlign: 'center' as const, color: 'var(--c-ink)', fontWeight: 600 }

/* 计算跟踪项目数量（排除已完成/取消/暂停） */
const trackingCount = computed(() => {
  return projects.value.filter(p => !['completed', 'cancelled', 'paused'].includes(p.status)).length
})

/* 计算重要项目数量（优先级为 urgent） */
const importantCount = computed(() => {
  return projects.value.filter(p =>
    p.urgency === 'urgent' && !['completed', 'cancelled', 'paused'].includes(p.status)
  ).length
})

/* 排序/比较工具 */
const collator = new Intl.Collator('zh-Hans-CN')
function cmpStr(a?: string | null, b?: string | null) {
  return collator.compare(a || '', b || '')
}
function cmpStatus(a: Project, b: Project) {
  return PROJECT_STATUS_ORDER.indexOf(a.status) - PROJECT_STATUS_ORDER.indexOf(b.status)
}

/* 最新进展状态（用于"项目进展"列筛选） */
function latestStatusOf(p: Project): string {
  const log = p.progress_log ?? []
  if (!log.length) return ''
  return [...log].sort((a, b) => (a.time || '').localeCompare(b.time || ''))[log.length - 1].status || ''
}

/* 表头排序方法（el-table sort-method） */
const sortDept = (a: Project, b: Project) => cmpStr(getDepartmentShortName(a.department), getDepartmentShortName(b.department))
const sortOwner = (a: Project, b: Project) => cmpStr(a.owner_name, b.owner_name)
const sortUrgency = (a: Project, b: Project) => urgWeight(b.urgency) - urgWeight(a.urgency)

/* 表头筛选方法（el-table filter-method）：按部门简称匹配 */
const filterDept = (value: string, row: Project) => getDepartmentShortName(row.department) === value
const filterOwner = (value: string, row: Project) => (row.owner_name || '') === value
const filterStatus = (value: string, row: Project) => row.status === value
const filterUrgency = (value: string, row: Project) => row.urgency === value
/* 项目进展：按最新进展状态筛选（无进展用空串） */
const filterProgress = (value: string, row: Project) => latestStatusOf(row) === value

/* 默认排序：部门简称 › 负责人 › 优先级(重要在前)，再叠加关键词过滤。
   预计算 _deptShort/_deptColor 并生成新对象，确保部门数据异步到达后 el-table 重渲染。 */
const rows = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  const list = projects.value.filter((p) => !kw || p.name.toLowerCase().includes(kw))
  return [...list]
    .sort((a, b) =>
      cmpStr(getDepartmentShortName(a.department), getDepartmentShortName(b.department))
      || cmpStr(a.owner_name, b.owner_name)
      || (urgWeight(b.urgency) - urgWeight(a.urgency)),
    )
    .map((p) => {
      const log = [...(p.progress_log ?? [])].sort((a, b) => (a.time || '').localeCompare(b.time || ''))
      return {
        ...p,
        _deptShort: getDepartmentShortName(p.department),
        _deptColor: getDepartmentColor(p.department),
        _lastProgress: log.length ? (log[log.length - 1].content || '') : '',
        _lastStatus: log.length ? (log[log.length - 1].status || '') : '',
        _recentProgress: [...log].slice(-8),
        _hasMore: log.length > 8,
      }
    })
})

/* 表头筛选项 */
function uniqueFilters(values: (string | null | undefined)[]) {
  const set = new Set(values.map((v) => v || ''))
  return [...set].filter((v) => v !== '').sort((a, b) => collator.compare(a, b))
    .map((v) => ({ text: v, value: v }))
}
/* 部门筛选项：按简称去重，每个部门只出现一次（无对应简称的变体值不进入筛选） */
const deptFilters = computed(() => {
  const shortNames = new Set<string>()
  for (const p of projects.value) {
    const sn = getDepartmentShortName(p.department)
    if (sn) shortNames.add(sn)
  }
  return [...shortNames].sort((a, b) => collator.compare(a, b))
    .map((sn) => ({ text: sn, value: sn }))
})
const ownerFilters = computed(() => uniqueFilters(projects.value.map((p) => p.owner_name)))
const deptValues = computed(() => deptFilters.value.map((f) => f.value))
const ownerValues = computed(() => ownerFilters.value.map((f) => f.value))
const statusFilters = PROJECT_STATUS_ORDER.map((s) => ({ text: projectStatusLabel[s], value: s }))
/* 默认筛选：隐藏已完成/已取消（用户可在筛选框勾选查看） */
const defaultStatusFiltered = PROJECT_STATUS_ORDER.filter((s) => s !== 'completed' && s !== 'cancelled')
const urgencyFilters = (['urgent', 'high', 'medium', 'low'] as ProjectUrgency[])
  .map((u) => ({ text: urgencyLabel[u], value: u }))
/* 项目进展筛选项：数据中实际出现的最新进展状态（按预设顺序），含"无进展" */
const progressFilters = computed(() => {
  const present = new Set(projects.value.map((p) => latestStatusOf(p)))
  const items: { text: string; value: string }[] = PROGRESS_STATUSES
    .filter((s) => present.has(s))
    .map((s) => ({ text: s, value: s }))
  if (present.has('')) items.push({ text: '无进展', value: '' })
  return items
})

async function load() {
  loading.value = true
  try {
    projects.value = await projectApi.list({ limit: 500 })
    currentRow.value = null
  } catch {
    ElMessage.error('加载项目失败')
  } finally {
    loading.value = false
  }
}

async function loadDepartments() {
  try {
    departments.value = await departmentApi.list({ limit: 100 })
  } catch {
    // 静默失败，部门颜色为可选功能
  }
}

/* 当前选中行（单击选中，供右上角操作图标使用） */
const currentRow = ref<Project | null>(null)
function onCurrentChange(row: Project | null) {
  currentRow.value = row
}

/* 详情抽屉（兼新建） */
const detailVisible = ref(false)
const detailProject = ref<Project | null>(null)
const createMode = ref(false)
function openDetail(row: Project) {
  createMode.value = false
  detailProject.value = row
  detailVisible.value = true
}

/* 右上角操作图标：作用于当前选中行 */
function detailSelected() {
  if (currentRow.value) openDetail(currentRow.value)
}
function removeSelected() {
  if (currentRow.value) remove(currentRow.value)
}

/* 删除 */
async function remove(row: Project) {
  try {
    await ElMessageBox.confirm(`确定删除项目「${row.name}」？此操作不可恢复。`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  try {
    await projectApi.remove(row.id)
    ElMessage.success('已删除')
    await load()
  } catch {
    ElMessage.error('删除失败（需要管理员或项目经理权限）')
  }
}

/* 新增：复用详情抽屉的新建模式 */
function openCreate() {
  createMode.value = true
  detailProject.value = null
  detailVisible.value = true
}

onMounted(() => {
  load()
  loadDepartments()
})
</script>

<style scoped>
.head-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--sp-3);
  margin-bottom: var(--sp-3);
}
.head-actions {
  display: flex;
  gap: var(--sp-1);
  align-items: center;
}
.badge { font-weight: 600; font-size: 12px; padding: 2px 8px; border-radius: var(--r-sm); }
.urg { font-weight: 600; }
.link { color: var(--c-accent); cursor: pointer; font-weight: 500; }
.link:hover { text-decoration: underline; }
.progress-cell { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.prog-status { font-weight: 600; }

.tbar { display: inline-block; width: 70px; height: 6px; background: var(--c-canvas); border-radius: 999px; overflow: hidden; vertical-align: middle; }
.tbar-fill { height: 100%; border-radius: 999px; }
.tpct { margin-left: var(--sp-2); font-size: 12px; color: var(--c-ink-2); }
.long-term-text { font-weight: 700; color: var(--c-accent); font-size: 13px; }
.overdue { color: var(--c-status-overdue); font-weight: 600; }

.footer-bar { margin-top: var(--sp-3); font-size: 13px; }
:deep(.el-table) { --el-table-border-color: var(--c-border); }
</style>

<!-- 「说明」列 tooltip 样式：浅棕背景 + 黑字 + 合适尺寸。
     tooltip 通过 teleport 挂到 body，必须用非 scoped 全局样式才能命中。 -->
<style>
.el-popper.desc-tip.is-light {
  max-width: 360px;
  background: #f5ecd9;            /* 浅棕背景 */
  color: #1a1a1a;                 /* 黑色文字 */
  border-color: #e0d3b8;
  line-height: 1.6;
  white-space: normal;           /* 自动换行，避免过长 */
  word-break: break-word;
}
.el-popper.desc-tip.is-light .el-popper__arrow::before {
  background: #f5ecd9;
  border-color: #e0d3b8;
}

/* 「项目进展」列 tooltip：最近 8 条进展记录 */
.el-popper.progress-tip.is-light {
  max-width: 480px;
  background: #f5ecd9;
  color: #1a1a1a;
  border-color: #e0d3b8;
  padding: 8px 12px;
}
.el-popper.progress-tip .ptip-more {
  text-align: center; color: #8a7a55; font-weight: 700; line-height: 1; margin-bottom: 6px;
}
.el-popper.progress-tip .ptip-item {
  display: flex; gap: 10px; padding: 4px 0; line-height: 1.5;
  border-top: 1px dashed #e0d3b8;
}
.el-popper.progress-tip .ptip-item:first-of-type { border-top: none; }
.el-popper.progress-tip .ptip-time { color: #8a7a55; font-size: 12px; white-space: nowrap; flex-shrink: 0; }
.el-popper.progress-tip .ptip-text { word-break: break-word; white-space: normal; }
.el-popper.progress-tip .ptip-meeting { color: #1a73e8; font-weight: 700; }
.el-popper.progress-tip .el-popper__arrow::before {
  background: #f5ecd9;
  border-color: #e0d3b8;
}
</style>
