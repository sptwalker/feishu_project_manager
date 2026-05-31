<template>
  <el-drawer
    :model-value="visible"
    size="62%"
    :with-header="false"
    @update:model-value="onVisible"
  >
    <div v-if="local" class="detail">
      <el-button
        v-if="!createMode"
        class="edit-btn"
        :type="editing ? 'warning' : 'primary'"
        :icon="editing ? Close : EditPen"
        size="large"
        @click="toggleEdit"
      >{{ editing ? '取消编辑' : '项目编辑' }}</el-button>
      <!-- 标题 -->
      <div class="d-head" :style="{ '--bar': statusColor(local.status) }">
        <div class="d-title-row">
          <span v-if="!editing" class="d-title">{{ local.name }}</span>
          <el-input v-else v-model="form.name" size="large" class="d-title-input" placeholder="请输入项目名称" />
          <span v-if="meeting.active" class="meeting-banner">第{{ meeting.currentCount }}次周会记录中……</span>
        </div>
        <div v-if="!editing" class="d-badges">
          <span class="badge" :style="{ color: statusColor(local.status), background: 'var(--c-surface-2)' }">
            {{ statusLabel(local.status) }}
          </span>
          <span class="badge" :style="{ color: urgColor(local.urgency), background: 'var(--c-surface-2)' }">
            {{ urgText(local.urgency) }}
          </span>
          <span v-if="overdue" class="badge overdue">逾期</span>
        </div>
      </div>

      <!-- 简要说明（对应表格“说明”字段） -->
      <div class="brief-block">
        <div class="mini-label">简要说明</div>
        <div v-if="!editing" class="brief">{{ local.content || '—' }}</div>
        <el-input v-else v-model="form.content" type="textarea" :rows="2" placeholder="一句话简要说明" />
      </div>

      <!-- 完成度 -->
      <div class="prog-block">
        <div class="prog-head">
          <span class="mini-label">完成度</span>
          <span class="num pct">{{ editing ? form.completion : local.completion }}%</span>
        </div>
        <el-slider v-if="editing" v-model="form.completion" :min="0" :max="100" />
        <div v-else class="bar"><div class="bar-fill" :style="{ width: local.completion + '%', background: statusColor(local.status) }" /></div>
      </div>

      <!-- 字段网格 -->
      <dl class="d-fields">
        <div class="f">
          <dt>部门<span v-if="createMode" class="req">*</span></dt>
          <dd v-if="!editing" :style="{ color: getDepartmentColor(local.department), fontWeight: local.department ? 600 : 400 }">
            {{ local.department || '—' }}
          </dd>
          <el-select v-else v-model="form.department" filterable allow-create default-first-option clearable placeholder="选择/输入" size="small">
            <el-option v-for="dept in departmentList" :key="dept.name" :label="dept.name" :value="dept.name">
              <span :style="{ color: dept.color || 'inherit', fontWeight: 600 }">{{ dept.name }}</span>
            </el-option>
          </el-select>
        </div>
        <div class="f">
          <dt>负责人<span v-if="createMode" class="req">*</span></dt>
          <dd v-if="!editing">{{ local.owner_name || '—' }}</dd>
          <el-select v-else v-model="form.owner_name" filterable allow-create default-first-option clearable placeholder="选择/输入" size="small">
            <el-option v-for="o in ownerOptions" :key="o" :label="o" :value="o" />
          </el-select>
        </div>
        <div class="f">
          <dt>相关人</dt>
          <dd v-if="!editing">{{ local.related_name || '—' }}</dd>
          <el-input v-else v-model="form.related_name" size="small" placeholder="多个用、分隔" />
        </div>
        <div class="f">
          <dt>完成情况</dt>
          <dd v-if="!editing">{{ statusLabel(local.status) }}</dd>
          <el-select v-else v-model="form.status" size="small">
            <el-option v-for="s in PROJECT_STATUS_ORDER" :key="s" :label="statusLabel(s)" :value="s" />
          </el-select>
        </div>
        <div class="f">
          <dt>优先级<span v-if="createMode" class="req">*</span></dt>
          <dd v-if="!editing">{{ urgText(local.urgency) }}</dd>
          <el-select v-else v-model="form.urgency" size="small">
            <el-option v-for="u in urgencyOptions" :key="u.value" :label="u.label" :value="u.value" />
          </el-select>
        </div>
        <div class="f">
          <dt>记录日期</dt>
          <dd v-if="!editing">{{ local.record_date || '—' }}</dd>
          <el-date-picker v-else v-model="form.record_date" type="date" value-format="YYYY-MM-DD" size="small" style="width: 100%" />
        </div>
        <div class="f">
          <dt>截止日期</dt>
          <dd v-if="!editing">{{ local.estimated_end_date || '—' }}</dd>
          <el-date-picker v-else v-model="form.estimated_end_date" type="date" value-format="YYYY-MM-DD" size="small" style="width: 100%" />
        </div>
      </dl>

      <div v-if="editing" class="edit-actions">
        <el-button @click="onCancel">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">{{ createMode ? '创建项目' : '保存' }}</el-button>
      </div>

      <!-- 项目进展详情 -->
      <div ref="progressWrap" class="progress-block">
        <div class="prog-title">
          <span class="mini-label">项目进展详情</span>
          <span class="hint muted">{{ createMode ? '请填写首次进展记录（必填）' : editingProgress ? '编辑中 · 点击空白处保存并收起' : '点击下方区域编辑' }}</span>
        </div>

        <!-- 编辑态：可编辑表格 -->
        <div v-if="editingProgress" class="prog-edit">
          <table class="prog-table">
            <thead>
              <tr><th style="width:180px">更新时间</th><th>内容</th><th style="width:130px">状况</th><th style="width:44px"></th></tr>
            </thead>
            <tbody>
              <tr v-for="(e, i) in progressDraft" :key="i">
                <td><el-date-picker v-model="e.time" type="datetime" value-format="YYYY-MM-DD HH:mm" size="small" style="width: 100%" /></td>
                <td>
                  <div class="content-cell">
                    <span v-if="meeting.active && i === progressDraft.length - 1" class="meeting-tag">周会记录：</span>
                    <el-input v-model="e.content" size="small" type="textarea" :autosize="{ minRows: 1, maxRows: 4 }" placeholder="进展内容" />
                  </div>
                </td>
                <td>
                  <el-select v-model="e.status" size="small">
                    <el-option v-for="s in PROGRESS_STATUSES" :key="s" :label="s" :value="s">
                      <span class="dot" :style="{ background: progressColor(s) }" />{{ s }}
                    </el-option>
                  </el-select>
                </td>
                <td><el-icon class="row-del" @click="removeRow(i)"><Delete /></el-icon></td>
              </tr>
              <tr v-if="!progressDraft.length">
                <td colspan="4" class="empty-row muted">暂无记录，点击下方“添加一条”</td>
              </tr>
            </tbody>
          </table>
          <el-button text type="primary" :icon="Plus" size="small" @click="addRow">添加一条</el-button>
        </div>

        <!-- 展示态：时间线 -->
        <div v-else class="prog-view" @click="enterProgressEdit">
          <div v-if="timeline.length" class="timeline">
            <div v-for="(e, i) in timeline" :key="i" class="tl-item">
              <span class="tl-node" :style="{ background: progressColor(e.status) }" />
              <div class="tl-body">
                <div class="tl-meta">
                  <span class="tl-time num">{{ e.time || '—' }}</span>
                  <span class="tl-status" :style="{ color: progressColor(e.status) }">{{ e.status }}</span>
                </div>
                <div class="tl-content"><span v-if="e.meeting_session" class="meeting-prefix">【第{{ e.meeting_session }}次周会更新】</span>{{ e.content || '（无内容）' }}</div>
              </div>
            </div>
          </div>
          <div v-else class="tl-empty muted">暂无进展记录，点击此处添加</div>
        </div>
      </div>

      <!-- 快捷入口 -->
      <div v-if="!createMode" class="d-links">
        <el-button text type="primary" @click="goTasks">查看任务 →</el-button>
        <el-button text type="primary" @click="goRisks">查看风险 →</el-button>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useMeetingStore } from '@/stores/meeting'
import { ElMessage } from 'element-plus'
import { EditPen, Close, Delete, Plus } from '@element-plus/icons-vue'
import { projectApi, departmentApi } from '@/api/resources'
import type { Project, ProjectStatus, ProjectUrgency, ProgressEntry, Department } from '@/types'
import {
  projectStatusLabel, projectStatusColor, urgencyLabel, urgencyColor,
  PROJECT_STATUS_ORDER, PROGRESS_STATUSES, progressStatusColor, isOverdue,
} from '@/utils/labels'

const props = withDefaults(defineProps<{
  visible: boolean
  project: Project | null
  departments?: string[]
  owners?: string[]
  createMode?: boolean
}>(), { departments: () => [], owners: () => [], createMode: false })

const emit = defineEmits<{
  (e: 'update:visible', v: boolean): void
  (e: 'updated'): void
}>()

const router = useRouter()
const meeting = useMeetingStore()
const departmentList = ref<Department[]>([])

const statusLabel = (s: ProjectStatus) => projectStatusLabel[s]
const statusColor = (s: ProjectStatus) => projectStatusColor[s]
const urgText = (u: ProjectUrgency) => urgencyLabel[u]
const urgColor = (u: ProjectUrgency) => urgencyColor[u]
const progressColor = (s: string) => progressStatusColor[s] || 'var(--c-ink-3)'

function getDepartmentColor(deptName?: string | null) {
  if (!deptName) return undefined
  const dept = departmentList.value.find(d => d.name === deptName)
  return dept?.color || undefined
}

const urgencyOptions = [
  { value: 'low', label: '低' }, { value: 'medium', label: '中' },
  { value: 'high', label: '高' }, { value: 'urgent', label: '重要' },
]

/* 本地快照（编辑保存后用接口返回刷新，避免依赖父组件刷新） */
const local = ref<Project | null>(null)
const editing = ref(false)
const saving = ref(false)

const form = reactive<Record<string, unknown>>({
  name: '', content: '', department: '', owner_name: '', related_name: '',
  status: 'planned', urgency: 'medium', completion: 0, record_date: '', estimated_end_date: null,
})

function resetForm() {
  if (!local.value) return
  Object.assign(form, {
    name: local.value.name,
    content: local.value.content ?? '',
    department: local.value.department ?? '',
    owner_name: local.value.owner_name ?? '',
    related_name: local.value.related_name ?? '',
    status: local.value.status,
    urgency: local.value.urgency,
    completion: local.value.completion,
    record_date: local.value.record_date,
    estimated_end_date: local.value.estimated_end_date ?? null,
  })
}

function sync() {
  if (props.createMode) {
    local.value = blankProject()
    Object.assign(form, {
      name: '', content: '', department: '', owner_name: '', related_name: '',
      status: 'planned', urgency: 'medium', completion: 0,
      record_date: todayStr(), estimated_end_date: null,
    })
    progressDraft.value = [{ time: nowStr(), content: '', status: '正常' }]
    editing.value = true
    editingProgress.value = true
    return
  }
  local.value = props.project ? { ...props.project } : null
  resetForm()
  progressDraft.value = (local.value?.progress_log ?? []).map((e) => ({ ...e }))
  editing.value = false
  editingProgress.value = false
}

watch(() => props.project, sync)
watch(() => props.visible, (v) => { if (v) sync() })

const overdue = computed(() => !!local.value && isOverdue(local.value.estimated_end_date, local.value.status))

const ownerOptions = computed(() => uniq([...(props.owners || []), form.owner_name as string, local.value?.owner_name || '']))
function uniq(arr: (string | undefined | null)[]): string[] {
  return [...new Set(arr.map((x) => (x || '').trim()).filter(Boolean))]
}

function toggleEdit() {
  if (editing.value) { cancelEdit() } else { resetForm(); editing.value = true }
}
function cancelEdit() {
  resetForm()
  editing.value = false
}

async function saveFields() {
  if (!local.value) return
  if (!form.name || !String(form.name).trim()) {
    ElMessage.warning('项目名称不能为空')
    return
  }
  saving.value = true
  try {
    const payload: Record<string, unknown> = {
      name: form.name,
      content: form.content || null,
      department: form.department || null,
      owner_name: form.owner_name || null,
      related_name: form.related_name || null,
      status: form.status,
      urgency: form.urgency,
      completion: form.completion,
      record_date: form.record_date,
      estimated_end_date: form.estimated_end_date || null,
    }
    const updated = await projectApi.update(local.value.id, payload as Partial<Project>)
    local.value = updated
    resetForm()
    editing.value = false
    emit('updated')
    ElMessage.success('已保存')
  } catch {
    ElMessage.error('保存失败（需要管理员或项目经理权限）')
  } finally {
    saving.value = false
  }
}

async function saveCreate() {
  if (!String(form.name).trim()) { ElMessage.warning('请输入项目名称'); return }
  if (!String(form.department).trim()) { ElMessage.warning('请选择或输入部门'); return }
  if (!String(form.owner_name).trim()) { ElMessage.warning('请选择或输入负责人'); return }
  if (!form.urgency) { ElMessage.warning('请选择优先级'); return }
  const firstProgress = progressDraft.value.filter((e) => (e.content || '').trim())
  if (!firstProgress.length) { ElMessage.warning('请填写首次进展记录'); return }
  saving.value = true
  try {
    const progress_log = firstProgress.map((e) => {
      const base = { time: e.time || nowStr(), content: e.content || '', status: e.status || '正常' }
      return e.meeting_session != null ? { ...base, meeting_session: e.meeting_session } : base
    })
    const payload: Record<string, unknown> = {
      name: form.name,
      content: form.content || null,
      department: form.department,
      owner_name: form.owner_name,
      related_name: form.related_name || null,
      status: form.status,
      urgency: form.urgency,
      completion: form.completion,
      record_date: form.record_date,
      estimated_end_date: form.estimated_end_date || null,
      progress_log,
    }
    await projectApi.create(payload as Partial<Project>)
    emit('updated')
    emit('update:visible', false)
    ElMessage.success('项目已创建')
  } catch {
    ElMessage.error('创建失败（需要管理员或项目经理权限）')
  } finally {
    saving.value = false
  }
}

function onCancel() {
  if (props.createMode) emit('update:visible', false)
  else cancelEdit()
}
function onSave() {
  if (props.createMode) saveCreate()
  else saveFields()
}

/* ---------- 项目进展详情：表格 ↔ 时间线 ---------- */
const editingProgress = ref(false)
const progressDraft = ref<ProgressEntry[]>([])
const progressWrap = ref<HTMLElement | null>(null)

// 时间线：按时间从过去到现在排列
const timeline = computed<ProgressEntry[]>(() =>
  [...(local.value?.progress_log ?? [])].sort((a, b) => (a.time || '').localeCompare(b.time || '')),
)

function nowStr(): string {
  const d = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

function todayStr(): string {
  return nowStr().slice(0, 10)
}

function blankProject(): Project {
  return {
    id: 0, name: '', record_date: todayStr(), content: null,
    status: 'planned' as ProjectStatus, urgency: 'medium' as ProjectUrgency,
    department: null, owner_name: null, related_name: null, completion: 0,
    estimated_end_date: null, actual_end_date: null, progress_log: null,
    created_at: '', updated_at: '',
  }
}

function enterProgressEdit() {
  if (!local.value) return
  progressDraft.value = (local.value.progress_log ?? []).map((e) => ({ ...e }))
  editingProgress.value = true
}
function addRow() {
  const entry: ProgressEntry = { time: nowStr(), content: '', status: '正常' }
  if (meeting.active) entry.meeting_session = meeting.currentCount
  progressDraft.value.push(entry)
}
function removeRow(i: number) {
  progressDraft.value.splice(i, 1)
}

async function commitProgress() {
  if (props.createMode) return
  if (!editingProgress.value || !local.value) return
  editingProgress.value = false
  const cleaned = progressDraft.value
    .filter((e) => (e.content || '').trim())
    .map((e) => {
      const base = { time: e.time || nowStr(), content: e.content || '', status: e.status || '正常' }
      return e.meeting_session != null ? { ...base, meeting_session: e.meeting_session } : base
    })
  // 无变化则不请求
  if (JSON.stringify(cleaned) === JSON.stringify(local.value.progress_log ?? [])) return
  try {
    const updated = await projectApi.update(local.value.id, { progress_log: cleaned } as Partial<Project>)
    local.value = updated
    emit('updated')
  } catch {
    ElMessage.error('保存进展失败（需要管理员或项目经理权限）')
  }
}

// 点击进展区域以外（且不在弹层内）时结束编辑
function onDocClick(e: MouseEvent) {
  if (!editingProgress.value) return
  const t = e.target as HTMLElement
  if (progressWrap.value?.contains(t)) return
  if (t.closest('.el-popper, .el-select-dropdown, .el-picker-panel, .el-picker__popper')) return
  commitProgress()
}

async function loadDepartments() {
  try {
    departmentList.value = await departmentApi.list({ limit: 100 })
  } catch {
    // 静默失败，部门颜色为可选功能
  }
}

onMounted(() => {
  document.addEventListener('click', onDocClick, true)
  loadDepartments()
})
onBeforeUnmount(() => document.removeEventListener('click', onDocClick, true))

function onVisible(v: boolean) {
  if (!v && !props.createMode && editingProgress.value) commitProgress()
  emit('update:visible', v)
}

function goTasks() {
  if (local.value) { emit('update:visible', false); router.push({ name: 'project-tasks', params: { id: local.value.id } }) }
}
function goRisks() {
  if (local.value) { emit('update:visible', false); router.push({ name: 'project-risks', params: { id: local.value.id } }) }
}
</script>

<style scoped>
.detail { display: flex; flex-direction: column; gap: var(--sp-5); padding: var(--sp-2) 0; position: relative; }
.edit-btn { position: absolute; top: 42px; right: 0; z-index: 2; font-size: 16px; }
.mini-label { font-size: 12px; color: var(--c-ink-3); margin-bottom: 4px; }

.d-head { border-left: 3px solid var(--bar); padding-left: var(--sp-3); padding-right: 124px; }
.d-title-row { display: flex; align-items: center; gap: var(--sp-2); margin-bottom: var(--sp-2); }
.req { color: var(--c-status-overdue); margin-left: 2px; }
.d-title { font-family: var(--font-display); font-size: 21px; font-weight: 700; }
.d-title-input { max-width: 420px; }
.edit-ico { cursor: pointer; color: var(--c-ink-3); font-size: 18px; }
.edit-ico:hover { color: var(--c-accent); }
.d-badges { display: flex; gap: var(--sp-2); flex-wrap: wrap; }
.badge { font-weight: 600; font-size: 12px; padding: 2px 10px; border-radius: var(--r-sm); }
.badge.overdue { color: var(--c-status-overdue); background: var(--c-status-overdue-soft); }

.brief { color: var(--c-ink-2); line-height: 1.6; font-size: 14px; }

.prog-block { }
.prog-head { display: flex; align-items: center; justify-content: space-between; }
.pct { font-weight: 600; color: var(--c-ink-2); }
.bar { height: 8px; background: var(--c-canvas); border-radius: 999px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 999px; transition: width 0.3s; }

.d-fields { display: grid; grid-template-columns: 1fr 1fr; gap: var(--sp-3) var(--sp-5); margin: 0; }
.f { display: flex; gap: var(--sp-3); align-items: center; }
.f dt { width: 64px; flex-shrink: 0; color: var(--c-ink-3); font-size: 13px; }
.f dd { margin: 0; color: var(--c-ink); font-weight: 500; }
.f :deep(.el-select), .f :deep(.el-input), .f :deep(.el-date-editor) { flex: 1; }

.edit-actions { display: flex; justify-content: flex-end; gap: var(--sp-2); }

/* 进展 */
.progress-block { border-top: 1px solid var(--c-border); padding-top: var(--sp-4); }
.prog-title { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: var(--sp-3); }
.hint { font-size: 12px; }

.prog-table { width: 100%; border-collapse: collapse; }
.prog-table th, .prog-table td { border: 1px solid var(--c-border); padding: 6px; vertical-align: top; text-align: left; }
.prog-table th { background: var(--c-surface-2); font-size: 12px; color: var(--c-ink-2); font-weight: 600; }
.empty-row { text-align: center; padding: var(--sp-3); }
.row-del { cursor: pointer; color: var(--c-ink-3); }
.row-del:hover { color: var(--c-status-overdue); }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }

.prog-view { cursor: pointer; border: 1px dashed transparent; border-radius: var(--r-md); padding: var(--sp-2); transition: border-color 0.15s, background 0.15s; }
.prog-view:hover { border-color: var(--c-border); background: var(--c-surface-2); }
.tl-empty { padding: var(--sp-4); text-align: center; font-size: 13px; }

.timeline { position: relative; padding-left: var(--sp-5); }
.timeline::before {
  content: ''; position: absolute; left: 7px; top: 4px; bottom: 4px;
  width: 2px; background: var(--c-border);
}
.tl-item { position: relative; padding-bottom: var(--sp-4); }
.tl-item:last-child { padding-bottom: 0; }
.tl-node {
  position: absolute; left: -22px; top: 3px;
  width: 12px; height: 12px; border-radius: 50%;
  border: 2px solid var(--c-surface); box-shadow: 0 0 0 1px var(--c-border);
}
.tl-meta { display: flex; align-items: center; gap: var(--sp-3); margin-bottom: 2px; }
.tl-time { font-size: 12px; color: var(--c-ink-3); }
.tl-status { font-size: 12px; font-weight: 600; }
.tl-content { font-size: 14px; color: var(--c-ink); line-height: 1.5; white-space: pre-wrap; }
.meeting-banner { margin-left: auto; color: #1a73e8; font-size: 18px; font-weight: 700; letter-spacing: 0.5px; }
.content-cell { display: flex; align-items: flex-start; gap: 4px; }
.meeting-tag { color: #1a73e8; font-weight: 600; font-size: 13px; white-space: nowrap; padding-top: 6px; }
.meeting-prefix { color: #1a73e8; font-weight: 700; }

.d-links { display: flex; gap: var(--sp-4); border-top: 1px solid var(--c-border); padding-top: var(--sp-4); }
</style>
