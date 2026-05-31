<template>
  <div class="page">
    <!-- 头部 -->
    <div class="thead">
      <div class="crumbs">
        <span class="link" @click="$router.push({ name: 'board' })">项目看板</span>
        <span class="sep">/</span>
        <span class="cur">{{ project?.name || '加载中…' }}</span>
      </div>
      <div class="head-actions">
        <el-button :icon="Upload" disabled>导入</el-button>
        <el-button :icon="Download" disabled>导出</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">新建任务</el-button>
      </div>
    </div>

    <!-- 项目概要条 -->
    <div v-if="project" class="summary">
      <div class="sum-progress">
        <span class="muted">进度</span>
        <div class="bar"><div class="bar-fill" :style="{ width: project.completion + '%' }" /></div>
        <span class="num">{{ project.completion }}%</span>
      </div>
      <div class="sum-stats">
        <span><b class="num">{{ tasks.length }}</b> 任务</span>
        <span><b class="num">{{ countBy('completed') }}</b> 完成</span>
        <span class="overdue"><b class="num">{{ overdueCount }}</b> 逾期</span>
      </div>
    </div>

    <!-- 任务 / 风险 切换 -->
    <div class="tabrow">
      <ProjectTabs :project-id="projectId" />
      <span v-if="viewMode === 'kanban'" class="drag-hint muted">提示：拖拽卡片到其它列可改变状态</span>
    </div>

    <!-- 工具栏：视图切换 + 筛选 -->
    <div class="toolbar">
      <el-radio-group v-model="viewMode" size="default">
        <el-radio-button value="kanban">看板</el-radio-button>
        <el-radio-button value="table">表格</el-radio-button>
      </el-radio-group>
      <div class="filters">
        <el-select v-model="filterPriority" placeholder="全部优先级" clearable style="width: 140px">
          <el-option v-for="p in priorityOptions" :key="p.value" :label="p.label" :value="p.value" />
        </el-select>
        <el-input v-model="keyword" placeholder="搜索任务" clearable :prefix-icon="Search" style="width: 200px" />
      </div>
    </div>

    <!-- 看板视图 -->
    <div v-if="viewMode === 'kanban'" v-loading="loading" class="kanban">
      <section
        v-for="col in TASK_STATUS_ORDER"
        :key="col"
        class="kcol"
        :class="{ 'drop-active': dragOverCol === col }"
        @dragover.prevent="dragOverCol = col"
        @dragleave="onDragLeave(col)"
        @drop="onDrop(col)"
      >
        <header class="kcol-head" :style="{ '--dot': statusColor(col) }">
          <span class="kdot" />
          <span class="kcol-title">{{ statusLabel(col) }}</span>
          <span class="kcol-count num">{{ grouped[col]?.length || 0 }}</span>
        </header>
        <div class="kcol-body">
          <article
            v-for="t in grouped[col]"
            :key="t.id"
            class="tcard"
            :class="{ dragging: draggedTask?.id === t.id }"
            :style="{ background: statusSoft(col) }"
            draggable="true"
            @dragstart="onDragStart(t)"
            @dragend="onDragEnd"
            @click="openEdit(t)"
          >
            <div class="tcard-top">
              <span class="tname">{{ t.name }}</span>
              <span v-if="overdue(t)" class="odot" title="逾期" />
            </div>
            <div class="tcard-meta">
              <span class="prio" :class="'prio-' + t.priority">{{ priorityText(t.priority) }}</span>
              <span v-if="t.due_date" class="muted">截止 {{ t.due_date }}</span>
            </div>
            <div v-if="t.status === 'in_progress'" class="tbar">
              <div class="tbar-fill" :style="{ width: t.completion + '%' }" />
            </div>
          </article>
          <el-empty v-if="!loading && !(grouped[col]?.length)" :image-size="0" description="—" />
        </div>
      </section>
    </div>

    <!-- 表格视图 -->
    <div v-else v-loading="loading">
      <el-table :data="filtered" stripe style="width: 100%" @row-click="openEdit">
        <el-table-column prop="name" label="任务名称" min-width="200" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <span class="badge" :style="{ color: statusColor(row.status), background: statusSoft(row.status) }">
              {{ statusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="优先级" width="90">
          <template #default="{ row }">
            <span class="prio" :class="'prio-' + row.priority">{{ priorityText(row.priority) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="完成度" width="140">
          <template #default="{ row }">
            <div class="tbar inline"><div class="tbar-fill" :style="{ width: row.completion + '%' }" /></div>
          </template>
        </el-table-column>
        <el-table-column prop="due_date" label="截止日期" width="130">
          <template #default="{ row }">
            <span :class="{ overdue: overdue(row) }">{{ row.due_date || '—' }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 任务创建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editing ? '编辑任务' : '新建任务'" width="480px">
      <el-form :model="form" label-width="84px" label-position="left">
        <el-form-item label="任务名称" required>
          <el-input v-model="form.name" placeholder="请输入任务名称" />
        </el-form-item>
        <el-form-item label="负责人">
          <el-input v-model="form.owner_name" placeholder="负责人姓名（可选）" style="width: 100%" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option v-for="s in TASK_STATUS_ORDER" :key="s" :label="statusLabel(s)" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="form.priority" style="width: 100%">
            <el-option v-for="p in priorityOptions" :key="p.value" :label="p.label" :value="p.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="完成度">
          <el-slider v-model="form.completion" :max="100" />
        </el-form-item>
        <el-form-item label="截止日期">
          <el-date-picker v-model="form.due_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button v-if="editing" type="danger" plain style="float: left" @click="remove">删除</el-button>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Upload, Download } from '@element-plus/icons-vue'
import { projectApi, taskApi } from '@/api/resources'
import type { Project, Task, TaskStatus, TaskPriority } from '@/types'
import {
  taskStatusLabel, taskStatusColor, taskStatusSoft, priorityLabel,
  TASK_STATUS_ORDER, isOverdue,
} from '@/utils/labels'
import ProjectTabs from '@/components/ProjectTabs.vue'

const props = defineProps<{ id: string }>()
const projectId = computed(() => Number(props.id))

const project = ref<Project | null>(null)
const tasks = ref<Task[]>([])
const loading = ref(false)
const viewMode = ref<'kanban' | 'table'>('kanban')
const filterPriority = ref<TaskPriority | ''>('')
const keyword = ref('')

const priorityOptions = [
  { value: 'low', label: '低' },
  { value: 'medium', label: '中' },
  { value: 'high', label: '高' },
]

const statusLabel = (s: TaskStatus) => taskStatusLabel[s]
const statusColor = (s: TaskStatus) => taskStatusColor[s]
const statusSoft = (s: TaskStatus) => taskStatusSoft[s]
const priorityText = (p: TaskPriority) => priorityLabel[p]
const overdue = (t: Task) => isOverdue(t.due_date, t.status)

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return tasks.value.filter((t) => {
    if (filterPriority.value && t.priority !== filterPriority.value) return false
    if (kw && !t.name.toLowerCase().includes(kw)) return false
    return true
  })
})

const grouped = computed<Record<TaskStatus, Task[]>>(() => {
  const g: Record<TaskStatus, Task[]> = { pending: [], in_progress: [], completed: [], blocked: [] }
  for (const t of filtered.value) g[t.status]?.push(t)
  return g
})

const overdueCount = computed(() => tasks.value.filter(overdue).length)
const countBy = (s: TaskStatus) => tasks.value.filter((t) => t.status === s).length

/* 看板拖拽改状态 */
const draggedTask = ref<Task | null>(null)
const dragOverCol = ref<TaskStatus | null>(null)

function onDragStart(t: Task) {
  draggedTask.value = t
}
function onDragEnd() {
  draggedTask.value = null
  dragOverCol.value = null
}
function onDragLeave(col: TaskStatus) {
  if (dragOverCol.value === col) dragOverCol.value = null
}

async function onDrop(col: TaskStatus) {
  const t = draggedTask.value
  dragOverCol.value = null
  draggedTask.value = null
  if (!t || t.status === col) return

  // 乐观更新：先本地切换，失败再回滚
  const prev = t.status
  const idx = tasks.value.findIndex((x) => x.id === t.id)
  if (idx >= 0) tasks.value[idx] = { ...tasks.value[idx], status: col }
  try {
    await taskApi.update(t.id, { status: col })
    ElMessage.success(`已移动到「${statusLabel(col)}」`)
  } catch {
    if (idx >= 0) tasks.value[idx] = { ...tasks.value[idx], status: prev }
    ElMessage.error('状态更新失败（可能无权限）')
  }
}

async function load() {
  loading.value = true
  try {
    const [p, ts] = await Promise.all([
      projectApi.get(projectId.value),
      taskApi.listByProject(projectId.value, { limit: 100 }),
    ])
    project.value = p
    tasks.value = ts
  } catch {
    ElMessage.error('加载任务失败')
  } finally {
    loading.value = false
  }
}

/* 创建 / 编辑 */
const dialogVisible = ref(false)
const editing = ref<Task | null>(null)
const saving = ref(false)
const form = reactive<Record<string, unknown>>({
  name: '', owner_name: '', status: 'pending', priority: 'medium', completion: 0, due_date: null,
})

function openCreate() {
  editing.value = null
  Object.assign(form, { name: '', owner_name: '', status: 'pending', priority: 'medium', completion: 0, due_date: null })
  dialogVisible.value = true
}

function openEdit(t: Task) {
  editing.value = t
  Object.assign(form, {
    name: t.name, owner_name: t.owner_name ?? '', status: t.status,
    priority: t.priority, completion: t.completion, due_date: t.due_date ?? null,
  })
  dialogVisible.value = true
}

async function submit() {
  if (!form.name) {
    ElMessage.warning('请填写任务名称')
    return
  }
  saving.value = true
  try {
    const payload: Record<string, unknown> = { ...form }
    if (!payload.due_date) delete payload.due_date
    if (!payload.owner_name) delete payload.owner_name
    if (editing.value) {
      await taskApi.update(editing.value.id, payload as Partial<Task>)
      ElMessage.success('任务已更新')
    } else {
      await taskApi.create(projectId.value, payload as Partial<Task>)
      ElMessage.success('任务已创建')
    }
    dialogVisible.value = false
    await load()
  } catch {
    ElMessage.error('保存失败（需要管理员或项目经理权限）')
  } finally {
    saving.value = false
  }
}

async function remove() {
  if (!editing.value) return
  try {
    await ElMessageBox.confirm('确定删除该任务？', '删除确认', { type: 'warning' })
  } catch {
    return
  }
  try {
    await taskApi.remove(editing.value.id)
    ElMessage.success('已删除')
    dialogVisible.value = false
    await load()
  } catch {
    ElMessage.error('删除失败（可能无权限）')
  }
}

onMounted(load)
</script>

<style scoped>
.thead {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--sp-4);
  flex-wrap: wrap;
  gap: var(--sp-3);
}
.crumbs { font-family: var(--font-display); font-size: 18px; font-weight: 600; }
.link { color: var(--c-ink-3); cursor: pointer; }
.link:hover { color: var(--c-accent); }
.sep { color: var(--c-ink-3); margin: 0 var(--sp-2); }
.cur { color: var(--c-ink); }
.head-actions { display: flex; gap: var(--sp-2); }

.summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-5);
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  padding: var(--sp-4) var(--sp-5);
  margin-bottom: var(--sp-4);
  flex-wrap: wrap;
}
.sum-progress { display: flex; align-items: center; gap: var(--sp-3); flex: 1; min-width: 240px; }
.sum-progress .bar { flex: 1; height: 8px; background: var(--c-canvas); border-radius: 999px; overflow: hidden; }
.sum-progress .bar-fill { height: 100%; background: var(--c-accent); border-radius: 999px; }
.sum-stats { display: flex; gap: var(--sp-5); font-size: 14px; color: var(--c-ink-2); }
.sum-stats b { color: var(--c-ink); margin-right: 4px; }
.sum-stats .overdue b { color: var(--c-status-overdue); }

.toolbar {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: var(--sp-4); gap: var(--sp-4); flex-wrap: wrap;
}
.filters { display: flex; gap: var(--sp-3); }

/* 看板 */
.kanban {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--sp-4);
  align-items: start;
}
@media (max-width: 980px) { .kanban { grid-template-columns: repeat(2, 1fr); } }
.kcol {
  background: var(--c-surface-2);
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  padding: var(--sp-3);
  min-height: 120px;
}
.kcol-head { display: flex; align-items: center; gap: var(--sp-2); padding: var(--sp-1) var(--sp-2) var(--sp-3); }
.kdot { width: 8px; height: 8px; border-radius: 50%; background: var(--dot); }
.kcol-title { font-family: var(--font-display); font-weight: 600; font-size: 14px; }
.kcol-count { margin-left: auto; color: var(--c-ink-3); font-size: 13px; font-weight: 600; }
.kcol-body { display: flex; flex-direction: column; gap: var(--sp-2); }

.tcard {
  border: 1px solid var(--c-border);
  border-radius: var(--r-sm);
  padding: var(--sp-3);
  cursor: pointer;
  transition: box-shadow 0.15s, transform 0.1s;
}
.tcard:hover { box-shadow: var(--shadow-md); transform: translateY(-1px); }
.tcard-top { display: flex; align-items: start; justify-content: space-between; gap: var(--sp-2); }
.tname { font-weight: 600; color: var(--c-ink); font-size: 14px; line-height: 1.35; }
.odot { width: 8px; height: 8px; border-radius: 50%; background: var(--c-status-overdue); flex-shrink: 0; margin-top: 5px; }
.tcard-meta { display: flex; align-items: center; gap: var(--sp-2); margin-top: var(--sp-2); font-size: 12px; }

.prio { font-weight: 600; font-size: 12px; padding: 1px 7px; border-radius: var(--r-sm); }
.prio-high { color: var(--c-status-overdue); background: var(--c-status-overdue-soft); }
.prio-medium { color: var(--c-accent); background: var(--c-accent-soft); }
.prio-low { color: var(--c-ink-3); background: var(--c-surface-2); }

.tbar { height: 5px; background: rgba(0,0,0,0.06); border-radius: 999px; overflow: hidden; margin-top: var(--sp-2); }
.tbar.inline { margin: 0; }
.tbar-fill { height: 100%; background: var(--c-status-progress); border-radius: 999px; }

.badge { font-weight: 600; font-size: 12px; padding: 2px 8px; border-radius: var(--r-sm); }
.overdue { color: var(--c-status-overdue); font-weight: 600; }
:deep(.el-table) { --el-table-border-color: var(--c-border); cursor: pointer; }
</style>
