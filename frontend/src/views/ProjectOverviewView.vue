<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">项目总览</h1>
        <p class="muted">以表格形式查看全部项目（默认按 部门 › 负责人 › 优先级 排序）</p>
      </div>
      <div class="head-actions">
        <el-input
          v-model="keyword" placeholder="搜索项目名称" clearable
          :prefix-icon="Search" style="width: 220px"
        />
        <span class="action-icons">
          <el-button text :icon="View" :disabled="!currentRow" @click="detailSelected">详情</el-button>
          <el-button text type="danger" :icon="Delete" :disabled="!currentRow" @click="removeSelected">删除</el-button>
        </span>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增项目</el-button>
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
        <template #default="{ row }">{{ row.department || '—' }}</template>
      </el-table-column>

      <el-table-column
        prop="status" label="完成情况" width="130"
        sortable :sort-method="cmpStatus"
        :filters="statusFilters" :filter-method="filterStatus"
      >
        <template #default="{ row }">
          <span class="badge" :style="{ color: statusColor(row.status), background: 'var(--c-surface-2)' }">
            {{ statusLabel(row.status) }}
          </span>
        </template>
      </el-table-column>

      <el-table-column prop="name" label="待办事项 / 项目名称" min-width="240" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="link" @click="openDetail(row)">{{ row.name }}</span>
        </template>
      </el-table-column>

      <el-table-column
        prop="content" label="说明" min-width="320"
        :show-overflow-tooltip="descTooltip"
      >
        <template #default="{ row }">{{ row.content || '—' }}</template>
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
          <div class="tbar"><div class="tbar-fill" :style="{ width: row.completion + '%', background: statusColor(row.status) }" /></div>
          <span class="num tpct">{{ row.completion }}%</span>
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

    <!-- 新增项目对话框 -->
    <el-dialog v-model="createVisible" title="新增项目" width="480px">
      <el-form :model="form" label-width="92px" label-position="left">
        <el-form-item label="项目名称" required>
          <el-input v-model="form.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="记录日期" required>
          <el-date-picker v-model="form.record_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="负责人">
          <el-input v-model="form.owner_name" placeholder="负责人姓名（可选）" />
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="form.department" placeholder="可选" />
        </el-form-item>
        <el-form-item label="完成情况">
          <el-select v-model="form.status" style="width: 100%">
            <el-option v-for="s in PROJECT_STATUS_ORDER" :key="s" :label="statusLabel(s)" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="form.urgency" style="width: 100%">
            <el-option v-for="u in urgencyOptions" :key="u.value" :label="u.label" :value="u.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="进度">
          <el-input-number v-model="form.completion" :min="0" :max="100" style="width: 100%" />
        </el-form-item>
        <el-form-item label="截止日期">
          <el-date-picker v-model="form.estimated_end_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <ProjectDetailDrawer
      v-model:visible="detailVisible"
      :project="detailProject"
      :departments="deptValues"
      :owners="ownerValues"
      @updated="load"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, View, Delete } from '@element-plus/icons-vue'
import { projectApi } from '@/api/resources'
import type { Project, ProjectStatus, ProjectUrgency } from '@/types'
import {
  projectStatusLabel, projectStatusColor, urgencyLabel, urgencyColor,
  urgencyWeight, PROJECT_STATUS_ORDER, isOverdue,
} from '@/utils/labels'
import ProjectDetailDrawer from '@/components/ProjectDetailDrawer.vue'

const projects = ref<Project[]>([])
const loading = ref(false)
const keyword = ref('')

const statusLabel = (s: ProjectStatus) => projectStatusLabel[s]
const statusColor = (s: ProjectStatus) => projectStatusColor[s]
const urgText = (u: ProjectUrgency) => urgencyLabel[u]
const urgColor = (u: ProjectUrgency) => urgencyColor[u]
const urgWeight = (u: ProjectUrgency) => urgencyWeight[u] ?? 0

/* 表头：文字居中 + 黑色 */
const headerCellStyle = { textAlign: 'center' as const, color: 'var(--c-ink)', fontWeight: 600 }

/* 「说明」列 tooltip：显示在下方、浅棕背景黑字、合适尺寸 */
const descTooltip = { placement: 'bottom' as const, effect: 'light' as const, popperClass: 'desc-tip' }

const urgencyOptions = [
  { value: 'low', label: '低' }, { value: 'medium', label: '中' },
  { value: 'high', label: '高' }, { value: 'urgent', label: '紧急' },
]

/* 排序/比较工具 */
const collator = new Intl.Collator('zh-Hans-CN')
function cmpStr(a?: string | null, b?: string | null) {
  return collator.compare(a || '', b || '')
}
function cmpStatus(a: Project, b: Project) {
  return PROJECT_STATUS_ORDER.indexOf(a.status) - PROJECT_STATUS_ORDER.indexOf(b.status)
}

/* 表头排序方法（el-table sort-method） */
const sortDept = (a: Project, b: Project) => cmpStr(a.department, b.department)
const sortOwner = (a: Project, b: Project) => cmpStr(a.owner_name, b.owner_name)
const sortUrgency = (a: Project, b: Project) => urgWeight(b.urgency) - urgWeight(a.urgency)

/* 表头筛选方法（el-table filter-method） */
const filterDept = (value: string, row: Project) => (row.department || '') === value
const filterOwner = (value: string, row: Project) => (row.owner_name || '') === value
const filterStatus = (value: string, row: Project) => row.status === value
const filterUrgency = (value: string, row: Project) => row.urgency === value

/* 默认排序：部门 › 负责人 › 优先级(紧急在前)，再叠加关键词过滤 */
const rows = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  const list = projects.value.filter((p) => !kw || p.name.toLowerCase().includes(kw))
  return [...list].sort((a, b) =>
    cmpStr(a.department, b.department)
    || cmpStr(a.owner_name, b.owner_name)
    || (urgWeight(b.urgency) - urgWeight(a.urgency)),
  )
})

/* 表头筛选项 */
function uniqueFilters(values: (string | null | undefined)[]) {
  const set = new Set(values.map((v) => v || ''))
  return [...set].filter((v) => v !== '').sort((a, b) => collator.compare(a, b))
    .map((v) => ({ text: v, value: v }))
}
const deptFilters = computed(() => uniqueFilters(projects.value.map((p) => p.department)))
const ownerFilters = computed(() => uniqueFilters(projects.value.map((p) => p.owner_name)))
const deptValues = computed(() => deptFilters.value.map((f) => f.value))
const ownerValues = computed(() => ownerFilters.value.map((f) => f.value))
const statusFilters = PROJECT_STATUS_ORDER.map((s) => ({ text: projectStatusLabel[s], value: s }))
const urgencyFilters = (['urgent', 'high', 'medium', 'low'] as ProjectUrgency[])
  .map((u) => ({ text: urgencyLabel[u], value: u }))

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

/* 当前选中行（单击选中，供右上角操作图标使用） */
const currentRow = ref<Project | null>(null)
function onCurrentChange(row: Project | null) {
  currentRow.value = row
}

/* 详情抽屉 */
const detailVisible = ref(false)
const detailProject = ref<Project | null>(null)
function openDetail(row: Project) {
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

/* 新增 */
const createVisible = ref(false)
const saving = ref(false)
const form = reactive<Record<string, unknown>>({
  name: '', record_date: '', owner_name: '', department: '',
  status: 'planned', urgency: 'medium', completion: 0, estimated_end_date: null,
})
function openCreate() {
  Object.assign(form, {
    name: '', record_date: new Date().toISOString().slice(0, 10), owner_name: '', department: '',
    status: 'planned', urgency: 'medium', completion: 0, estimated_end_date: null,
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
    if (!payload.owner_name) delete payload.owner_name
    if (!payload.department) delete payload.department
    if (!payload.estimated_end_date) delete payload.estimated_end_date
    await projectApi.create(payload as Partial<Project>)
    ElMessage.success('项目已创建')
    createVisible.value = false
    await load()
  } catch {
    ElMessage.error('创建失败（需要管理员或项目经理权限）')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.head-actions { display: flex; gap: var(--sp-3); align-items: center; }
.action-icons { display: inline-flex; gap: var(--sp-1); }
.badge { font-weight: 600; font-size: 12px; padding: 2px 8px; border-radius: var(--r-sm); }
.urg { font-weight: 600; }
.link { color: var(--c-accent); cursor: pointer; font-weight: 500; }
.link:hover { text-decoration: underline; }

.tbar { display: inline-block; width: 70px; height: 6px; background: var(--c-canvas); border-radius: 999px; overflow: hidden; vertical-align: middle; }
.tbar-fill { height: 100%; border-radius: 999px; }
.tpct { margin-left: var(--sp-2); font-size: 12px; color: var(--c-ink-2); }
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
</style>
