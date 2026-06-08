<template>
  <div class="detail-content-root" :class="`layout-${props.layout}`">
    <div v-if="local" class="detail">
      <div v-if="!createMode" class="edit-btn-group">
        <el-button
          class="edit-btn"
          :type="editing ? 'info' : 'primary'"
          :icon="editing ? Close : EditPen"
          size="large"
          @click="toggleEdit"
        >{{ editing ? '取消编辑' : '项目编辑' }}</el-button>
        <!-- 编辑按钮右侧插槽：会议页注入「新增项目」按钮 -->
        <slot name="header-extra" />
      </div>
      <!-- 标题 -->
      <div class="d-head" :style="{ '--bar': statusColor(local.status) }">
        <div class="d-title-row">
          <span v-if="!editing" class="d-title">{{ local.name }}</span>
          <!-- 标题后插槽：会议页注入「当前负责人内项目翻页」按钮 -->
          <slot v-if="!editing" name="title-after" />
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
          <!-- 记录时间：移到状态/优先级徽章之后，与徽章等间隔排列 -->
          <span v-if="!createMode && local.record_date" class="record-time">记录于 {{ local.record_date }}</span>
        </div>
      </div>

      <!-- 简要说明 + 完成度：会议页同排，抽屉仍各占一行（head-row 默认 display:contents） -->
      <div class="head-row">
        <!-- 简要说明（对应表格"说明"字段） -->
        <div class="brief-block">
          <div class="mini-label">简要说明</div>
          <div v-if="!editing" class="brief">{{ local.content || '—' }}</div>
          <el-input v-else v-model="form.content" type="textarea" :rows="2" placeholder="一句话简要说明" />
        </div>

        <!-- 完成度 / 长期项目 -->
        <div class="prog-block">
          <div class="prog-head">
            <span class="mini-label">完成度</span>
            <el-checkbox v-if="editing" v-model="form.is_long_term" size="small">长期项目</el-checkbox>
            <span v-if="isLong && !editing" class="long-term-text">长期项目</span>
            <span v-else-if="!isLong" class="num pct">{{ editing ? form.completion : local.completion }}%</span>
          </div>
          <el-slider v-if="editing && !form.is_long_term" v-model="form.completion" :min="0" :max="100" />
          <div v-else-if="!editing && !local.is_long_term" class="bar"><div class="bar-fill" :style="{ width: local.completion + '%', background: barFill(local.status) }" /></div>
        </div>
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
          <el-select v-else v-model="form.owner_name" filterable clearable placeholder="选择负责人（项目经理/管理员）" size="small">
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
          <dd v-if="!editing" :style="{ color: urgColor(local.urgency), fontWeight: 600 }">{{ urgText(local.urgency) }}</dd>
          <el-select v-else v-model="form.urgency" size="small">
            <el-option v-for="u in urgencyOptions" :key="u.value" :label="u.label" :value="u.value" />
          </el-select>
        </div>
        <div class="f">
          <dt>截止日期</dt>
          <dd v-if="!editing">{{ local.estimated_end_date || '—' }}</dd>
          <el-date-picker v-else v-model="form.estimated_end_date" type="date" value-format="YYYY-MM-DD" size="small" style="width: 100%" />
        </div>
      </dl>

      <div v-if="editing" class="edit-actions">
        <el-button v-if="!createMode && isAdmin" class="btn-delete-deep" :icon="Delete" :loading="deleting" @click="removeProject">删除</el-button>
        <el-button class="btn-amber" :icon="Check" :loading="saving" @click="onSave">{{ createMode ? '创建项目' : '保存' }}</el-button>
      </div>

      <!-- 项目进展 / 历史修改记录（tab 切换） -->
      <el-tabs v-model="activeTab" class="detail-tabs">
        <el-tab-pane label="进展详情" name="progress">
      <!-- 项目进展详情 -->
      <div ref="progressWrap" class="progress-block">
        <div class="prog-title">
          <span class="mini-label">项目进展详情</span>
          <!-- 进展编辑控制：编辑(蓝)进入；编辑态显示 取消(灰)放弃 + 保存(琥珀)提交；createMode 下随项目创建保存，不显示 -->
          <template v-if="!createMode">
            <el-button v-if="!editingProgress" size="small" class="pg-toggle-btn btn-blue" @click="enterProgressEdit">编辑</el-button>
            <template v-else>
              <el-button size="small" class="pg-toggle-btn" type="info" @click="cancelProgressEdit">取消</el-button>
              <el-button size="small" class="pg-toggle-btn btn-amber" @click="commitProgress">保存</el-button>
            </template>
          </template>
          <span v-if="stalled" class="stalled-tag" :style="{ color: stalled.color, fontWeight: stalled.bold ? 700 : 600 }">⏱超过{{ stalled.days }}无反馈</span>
          <span class="hint muted">{{ createMode ? '请填写首次进展记录（必填）' : editingProgress ? '编辑中 · 点击保存提交' : '右键点击记录可添加批注' }}</span>
        </div>

        <!-- 编辑态：可编辑表格 -->
        <div v-if="editingProgress" class="prog-edit">
          <!-- 「添加一条」置于表格上方：新增记录(时间=现在)在倒序时间线中显示在最上，按钮位置与之呼应 -->
          <el-button text type="primary" :icon="Plus" size="small" class="add-row-btn" @click="addRow">添加一条</el-button>
          <table class="prog-table">
            <thead>
              <tr><th style="width:180px">更新时间</th><th>内容</th><th style="width:130px">状况</th><th style="width:44px"></th></tr>
            </thead>
            <tbody>
              <!-- 编辑行按 draftView 倒序渲染（最新在上，与展示态一致）；操作回调经 draftIndex 还原数据下标 -->
              <tr v-for="(e, vi) in draftView" :key="vi">
                <td><el-date-picker v-model="e.time" type="datetime" value-format="YYYY-MM-DD HH:mm" size="small" style="width: 100%" :disabled-date="disabledFutureDate" /></td>
                <td>
                  <div class="content-cell">
                    <span v-if="e.reply_to" class="feedback-tag">反馈：</span>
                    <!-- 仅本次编辑会话中新增（_isNew）的行才显示标签；已有记录即便数据上带 meeting_session 也不显示 -->
                    <span v-else-if="meeting.active && e._isNew" class="meeting-tag">周会记录：</span>
                    <el-input v-model="e.content" size="small" type="textarea" :autosize="{ minRows: 1, maxRows: 4 }" placeholder="进展内容" />
                    <el-button
                      v-if="isPending(e.status) && !e.reply_to && !draftHasReply(e)"
                      text type="primary" size="small" class="feedback-btn"
                      @click="addFeedback(draftIndex(vi))"
                    >反馈</el-button>
                    <el-button
                      text type="primary" size="small" class="attach-btn"
                      :icon="Link"
                      @click="openAttachDialog(draftIndex(vi))"
                    >文档</el-button>
                  </div>
                  <!-- 附件列表（编辑态） -->
                  <div v-if="e.attachments && e.attachments.length" class="edit-attachments">
                    <div v-for="(att, ai) in e.attachments" :key="ai" class="edit-attach-item">
                      <el-icon class="attach-icon"><Document /></el-icon>
                      <a :href="att.url" target="_blank" class="attach-link">{{ att.title || att.url }}</a>
                      <el-icon class="attach-remove" @click="removeAttachment(draftIndex(vi), ai)"><Close /></el-icon>
                    </div>
                  </div>
                </td>
                <td>
                  <el-select v-model="e.status" size="small">
                    <el-option v-for="s in PROGRESS_STATUSES" :key="s" :label="s" :value="s">
                      <span class="dot" :style="{ background: progressColor(s) }" />{{ s }}
                    </el-option>
                  </el-select>
                </td>
                <td><el-icon class="row-del" @click="removeRow(draftIndex(vi))"><Delete /></el-icon></td>
              </tr>
              <tr v-if="!progressDraft.length">
                <td colspan="4" class="empty-row muted">暂无记录，点击上方"添加一条"</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 展示态：时间线（只读；编辑通过上方「编辑」按钮进入，不再点击区域进入） -->
        <div v-else class="prog-view">
          <div v-if="timeline.length" ref="timelineEl" class="timeline">
            <svg class="tl-svg" aria-hidden="true">
              <path
                v-for="(c, ci) in connectors" :key="ci"
                :d="c.d" :stroke="c.color" fill="none"
                stroke-width="2" stroke-dasharray="4 5" stroke-linecap="round"
              />
            </svg>
            <div v-for="(e, i) in timeline" :key="i" class="tl-item">
              <span
                v-if="e.reply_to"
                :ref="(el) => setNodeEl(el, i)"
                class="tl-node solid"
                :style="{ background: replyColor(e) }"
              />
              <span
                v-else-if="isPending(e.status)"
                :ref="(el) => setNodeEl(el, i)"
                class="tl-node hollow"
                :class="{ flashing: isFlashing(e) }"
                :style="{ '--nc': progressColor(e.status) }"
              />
              <span v-else :ref="(el) => setNodeEl(el, i)" class="tl-node solid" :style="{ background: progressColor(e.status) }" />
              <div class="tl-body">
                <div class="tl-meta">
                  <span class="tl-time num">{{ e.time || '—' }}</span>
                  <span class="tl-status" :style="{ color: e.reply_to ? replyColor(e) : progressColor(e.status) }">
                    {{ e.reply_to ? replyLabel(e) : e.status }}
                  </span>
                </div>
                <div class="tl-content" @contextmenu.prevent="onProgressContextMenu($event, e)">
                  <span v-if="e.meeting_session" class="meeting-prefix">【第{{ e.meeting_session }}次周会更新】</span>{{ e.content || '（无内容）' }}
                </div>
                <!-- 文档附件列表（展示态）：链接 @click.stop，避免点击冒泡到 .prog-view 触发进入编辑态 -->
                <div v-if="e.attachments && e.attachments.length" class="tl-attachments">
                  <div v-for="att in e.attachments" :key="att.url" class="tl-attach-item">
                    <el-icon class="attach-icon"><Document /></el-icon>
                    <a :href="att.url" target="_blank" class="attach-link" @click.stop>{{ att.title || '飞书文档' }}</a>
                  </div>
                </div>
                <!-- 批注列表 -->
                <div v-if="e.annotations && e.annotations.length" class="annotations">
                  <div v-for="ann in e.annotations" :key="ann.id" class="annotation" @contextmenu.prevent="onAnnotationContextMenu($event, e, ann)">
                    <div class="ann-header">
                      <span class="ann-author">{{ ann.author_name }}</span>
                      <span class="ann-time">{{ ann.created_at }}</span>
                    </div>
                    <div class="ann-content">{{ ann.content }}</div>
                    <!-- 回复列表 -->
                    <div v-if="ann.replies && ann.replies.length" class="ann-replies">
                      <div v-for="reply in ann.replies" :key="reply.id" class="ann-reply">
                        <div class="reply-header">
                          <span class="reply-author">{{ reply.author_name }}</span>
                          <span class="reply-time">{{ reply.created_at }}</span>
                        </div>
                        <div class="reply-content">{{ reply.content }}</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="stalled-banner">--- 暂无进展记录，点击编辑添加 ---</div>
        </div>

        <div v-if="stalled" class="stalled-banner">
          --- 已超过 <span class="stalled-banner-days" :style="{ color: stalled.color }">{{ stalled.days }}</span> 天没有进展反馈 ---
        </div>
      </div>
        </el-tab-pane>

        <el-tab-pane label="历史修改记录" name="history">
          <!-- 该项目所有编辑/操作日志（时间·编辑人·内容），持久化于操作日志，按项目过滤 -->
          <div v-loading="historyLoading" class="history-block">
            <div v-if="history.length" class="hist-list">
              <div v-for="h in history" :key="h.id" class="hist-row">
                <span class="hist-user">{{ h.user_name || '—' }}</span>
                <span class="hist-time">{{ fmtTime(h.occurred_at) }}</span>
                <span class="hist-desc">{{ h.description }}</span>
              </div>
            </div>
            <el-empty v-else-if="!historyLoading" description="暂无修改记录" :image-size="60" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 批注/回复对话框 -->
    <el-dialog
      v-model="annotationDialog.visible"
      :title="annotationDialog.mode === 'annotation' ? '添加批注' : '回复批注'"
      width="500px"
    >
      <el-input
        v-model="annotationDialog.content"
        type="textarea"
        :rows="4"
        :maxlength="annotationDialog.mode === 'annotation' ? 256 : 128"
        show-word-limit
        :placeholder="annotationDialog.mode === 'annotation' ? '请输入批注内容（不超过256字）' : '请输入回复内容（不超过128字）'"
      />
      <template #footer>
        <el-button @click="annotationDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="saveAnnotation">确定</el-button>
      </template>
    </el-dialog>

    <!-- 文档附件对话框 -->
    <el-dialog
      v-model="attachDialog.visible"
      title="添加飞书文档"
      width="500px"
    >
      <el-form label-width="80px">
        <el-form-item label="文档链接">
          <el-input
            v-model="attachDialog.url"
            placeholder="粘贴飞书文档链接，如 https://example.feishu.cn/docx/..."
            clearable
          />
        </el-form-item>
        <el-form-item label="文档标题">
          <el-input
            v-model="attachDialog.title"
            placeholder="可选，留空则显示链接"
            clearable
          />
        </el-form-item>
        <el-alert v-if="attachDialog.validating" type="info" :closable="false" show-icon>
          正在验证链接...
        </el-alert>
        <el-alert v-if="attachDialog.error" type="error" :closable="false" show-icon>
          {{ attachDialog.error }}
        </el-alert>
      </el-form>
      <template #footer>
        <el-button @click="attachDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="attachDialog.validating" @click="saveAttachment">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useMeetingStore } from '@/stores/meeting'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import { EditPen, Close, Delete, Plus, Check, Link, Document } from '@element-plus/icons-vue'
import { projectApi, departmentApi, userApi } from '@/api/resources'
import type { Project, ProjectStatus, ProjectUrgency, ProgressEntry, Department, Annotation, AnnotationReply, DocumentAttachment, OperationLog } from '@/types'
import {
  projectStatusLabel, projectStatusColor, urgencyLabel, urgencyColor,
  PROJECT_STATUS_ORDER, PROGRESS_STATUSES, PENDING_STATUSES, progressStatusColor, isOverdue,
} from '@/utils/labels'

const props = withDefaults(defineProps<{
  visible: boolean
  project: Project | null
  departments?: string[]
  owners?: string[]
  createMode?: boolean
  layout?: 'drawer' | 'meeting'
}>(), { departments: () => [], owners: () => [], createMode: false, layout: 'drawer' })

const emit = defineEmits<{
  (e: 'updated'): void
  (e: 'request-close'): void
}>()

const meeting = useMeetingStore()
const auth = useAuthStore()
const isAdmin = computed(() => auth.currentUser?.role === 'admin')
const departmentList = ref<Department[]>([])

/* 批注/回复作者名：优先英文名，缺失时回退中文名 */
const annotationAuthor = computed(() => auth.currentUser?.name_en?.trim() || auth.currentUser?.name || '')

const statusLabel = (s: ProjectStatus) => projectStatusLabel[s]
const statusColor = (s: ProjectStatus) => projectStatusColor[s]
// 完成度进度条填充：在状态色上叠加一层从左到右渐隐的白雾，形成同色「左淡右浓」的渐变（兼容 css 变量颜色）
const barFill = (s: ProjectStatus) =>
  `linear-gradient(90deg, rgba(255,255,255,0.6), rgba(255,255,255,0)), ${statusColor(s)}`
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

/* 历史修改记录 tab：当前激活 tab、历史日志列表、加载态 */
const activeTab = ref<'progress' | 'history'>('progress')
const history = ref<OperationLog[]>([])
const historyLoading = ref(false)

const form = reactive<Record<string, unknown>>({
  name: '', content: '', department: '', owner_name: '', related_name: '',
  status: 'planned', urgency: 'medium', completion: 0, is_long_term: false, record_date: '', estimated_end_date: null,
})

/* 是否长期项目（编辑态看草稿、展示态看本地） */
const isLong = computed(() => (editing.value ? !!form.is_long_term : !!local.value?.is_long_term))

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
    is_long_term: !!local.value.is_long_term,
    record_date: local.value.record_date,
    estimated_end_date: local.value.estimated_end_date ?? null,
  })
}

function sync() {
  if (props.createMode) {
    local.value = blankProject()
    Object.assign(form, {
      name: '', content: '', department: '', owner_name: '', related_name: '',
      status: 'planned', urgency: 'medium', completion: 0, is_long_term: false,
      record_date: todayStr(), estimated_end_date: null,
    })
    progressDraft.value = [{ time: nowStr(), content: '', status: '正常' }]
    editing.value = true
    editingProgress.value = true
    return
  }
  local.value = props.project ? { ...props.project } : null
  resetForm()
  // 深拷贝以保留 annotations
  progressDraft.value = JSON.parse(JSON.stringify(local.value?.progress_log ?? []))
  editing.value = false
  editingProgress.value = false
  // 切换项目时重置 tab 到进展、清空历史缓存
  activeTab.value = 'progress'
  history.value = []
}

watch(() => props.project, sync)
watch(() => props.visible, (v) => { if (v) sync() })

/* 切到「历史修改记录」tab：先把未保存的进展提交落库，再拉取该项目的历史日志 */
watch(activeTab, async (tab) => {
  if (tab !== 'history') return
  if (editingProgress.value) await commitProgress()
  await loadHistory()
})

/* 拉取当前项目的历史修改记录（createMode 或无 id 时跳过） */
async function loadHistory() {
  const id = local.value?.id
  if (props.createMode || !id) { history.value = []; return }
  historyLoading.value = true
  try {
    history.value = await projectApi.history(id)
  } catch {
    history.value = []
  } finally {
    historyLoading.value = false
  }
}

/* 历史时间格式化：后端 occurred_at 无时区，按本地展示到分钟 */
function fmtTime(s?: string | null): string {
  if (!s) return '—'
  return s.replace('T', ' ').slice(0, 16)
}

const overdue = computed(() => !!local.value && isOverdue(local.value.estimated_end_date, local.value.status))

/* 停滞分级：最新进展距今天数 → 颜色/加粗（与项目总览一致，仅 >30 天显示） */
const stalled = computed<{ days: number; color: string; bold: boolean } | null>(() => {
  const log = local.value?.progress_log ?? []
  if (!log.length) return null
  const lastTime = [...log].sort((a, b) => (a.time || '').localeCompare(b.time || ''))[log.length - 1].time || ''
  if (!lastTime) return null
  const days = Math.floor((Date.now() - new Date(lastTime.replace(' ', 'T')).getTime()) / 86400000)
  if (days <= 30) return null
  let color = '#9AA0A6'
  let bold = false
  if (days <= 40) color = '#9AA0A6'
  else if (days <= 50) color = '#E6B422'
  else if (days <= 60) color = '#E6A23C'
  else if (days <= 70) { color = '#FA8C16'; bold = true }
  else if (days <= 90) { color = '#F0492A'; bold = true }
  else { color = '#E5484D'; bold = true }
  return { days, color, bold }
})

/* 负责人候选：用户管理中「项目经理 + 管理员」的英文名（与账号关联）；
   另把当前项目负责人原值并入，保证存量值（历史中文名）仍能回显 */
const managerNames = ref<string[]>([])
const ownerOptions = computed(() => uniq([
  local.value?.owner_name || '',
  form.owner_name as string,
  ...managerNames.value,
]))
function uniq(arr: (string | undefined | null)[]): string[] {
  return [...new Set(arr.map((x) => (x || '').trim()).filter(Boolean))]
}

async function loadManagers() {
  try {
    const users = await userApi.list({ limit: 200 })
    managerNames.value = uniq(
      users
        .filter((u) => u.role === 'admin' || u.role === 'project_manager')
        .map((u) => u.name_en || ''),
    )
  } catch {
    // 静默失败，负责人候选为可选增强
  }
}

function toggleEdit() {
  if (editing.value) { cancelEdit() } else { resetForm(); editing.value = true }
}
function cancelEdit() {
  resetForm()
  editing.value = false
}

/* 是否乐观锁冲突（HTTP 409：项目已被他人修改） */
function isConflict(err: unknown): boolean {
  return (err as { response?: { status?: number } })?.response?.status === 409
}

/* 拉取项目最新数据刷新 local（含最新 version）；网络失败时静默保持现状 */
async function refreshLocal() {
  if (!local.value?.id) return
  try {
    local.value = await projectApi.get(local.value.id)
  } catch { /* 保持现状，由用户手动刷新 */ }
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
      is_long_term: form.is_long_term,
      estimated_end_date: form.estimated_end_date || null,
      version: local.value.version,   // 乐观锁：带上打开时持有的版本号
    }
    const updated = await projectApi.update(local.value.id, payload as Partial<Project>)
    local.value = updated
    resetForm()
    editing.value = false
    emit('updated')
    ElMessage.success('已保存')
  } catch (err) {
    if (isConflict(err)) {
      // 乐观锁冲突：刷新最新数据（含新 version），保留编辑态与表单草稿供用户核对
      await refreshLocal()
      ElMessage.warning('项目已被他人修改，已加载最新值，请核对后重新保存')
    } else {
      ElMessage.error('保存失败（需要管理员或项目经理权限）')
    }
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
  const future = findFutureProgress()
  if (future) { ElMessage.error(`进展「${future}」的更新时间晚于当前时间，请修正后再保存`); return }
  saving.value = true
  try {
    const progress_log = cleanDraft()
    const payload: Record<string, unknown> = {
      name: form.name,
      content: form.content || null,
      department: form.department,
      owner_name: form.owner_name,
      related_name: form.related_name || null,
      status: form.status,
      urgency: form.urgency,
      completion: form.completion,
      is_long_term: form.is_long_term,
      estimated_end_date: form.estimated_end_date || null,
      progress_log,
    }
    await projectApi.create(payload as Partial<Project>)
    emit('updated')
    emit('request-close')
    ElMessage.success('项目已创建')
  } catch {
    ElMessage.error('创建失败（需要管理员或项目经理权限）')
  } finally {
    saving.value = false
  }
}

function onSave() {
  if (props.createMode) saveCreate()
  else saveFields()
}

const deleting = ref(false)
async function removeProject() {
  if (!local.value || props.createMode) return
  try {
    await ElMessageBox.confirm(
      `确定删除项目「${local.value.name}」？此操作不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  deleting.value = true
  try {
    await projectApi.remove(local.value.id)
    ElMessage.success('项目已删除')
    emit('updated')
    emit('request-close')
  } catch {
    ElMessage.error('删除失败（需要管理员权限）')
  } finally {
    deleting.value = false
  }
}

/* ---------- 项目进展详情：表格 ↔ 时间线 ---------- */
const editingProgress = ref(false)
const progressDraft = ref<ProgressEntry[]>([])

/* 编辑态渲染视图：与展示态时间线一致按「上新下旧」倒序显示；
   数据 progressDraft 仍按时间升序存储（保存格式与对比逻辑不变），行操作经 draftIndex 换算回原数组下标 */
const draftView = computed(() => [...progressDraft.value].reverse())
const draftIndex = (vi: number) => progressDraft.value.length - 1 - vi
const progressWrap = ref<HTMLElement | null>(null)

// 进展记录统一排序：按更新时间从过去到现在升序（编辑态与展示态共用，保证排序一致）
const byTime = (a: ProgressEntry, b: ProgressEntry) => (a.time || '').localeCompare(b.time || '')

// 时间线：抽屉与会议页统一倒序展示（最新更新显示在最上面）
const timeline = computed<ProgressEntry[]>(() => {
  const sorted = [...(local.value?.progress_log ?? [])].sort(byTime)
  return sorted.reverse()
})

const isPending = (s?: string) => PENDING_STATUSES.includes((s || '') as typeof PENDING_STATUSES[number])
function genId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

/* 时间线派生：被反馈引用的原事件 id 集合，以及 原事件id→反馈事件 映射（取最新一条） */
const repliedMap = computed<Record<string, ProgressEntry>>(() => {
  const map: Record<string, ProgressEntry> = {}
  for (const e of timeline.value) {
    if (e.reply_to) {
      const prev = map[e.reply_to]
      if (!prev || (e.time || '') >= (prev.time || '')) map[e.reply_to] = e
    }
  }
  return map
})
// 未结束且未被反馈 → 闪烁
const isFlashing = (e: ProgressEntry) => isPending(e.status) && !(e.id && repliedMap.value[e.id])
// 该事件作为反馈，其指向的原事件状态色（实心点颜色）
function replyColor(e: ProgressEntry): string {
  if (!e.reply_to) return progressColor(e.status)
  const origin = timeline.value.find((x) => x.id === e.reply_to)
  return progressColor(origin?.status || e.status)
}
// 反馈事件的状态文字：待讨论→讨论已反馈，待确认→确认已反馈，待执行→执行已反馈
const FEEDBACK_LABEL: Record<string, string> = {
  待讨论: '讨论已反馈', 待确认: '确认已反馈', 待执行: '执行已反馈',
}
function replyLabel(e: ProgressEntry): string {
  return FEEDBACK_LABEL[e.status] || `${e.status}已反馈`
}

/* ---- 反馈连线（测量节点真实位置，SVG 平行线段+弧线绘制，不与主时间轴重合）---- */
const timelineEl = ref<HTMLElement | null>(null)
const nodeEls: HTMLElement[] = []
function setNodeEl(el: unknown, i: number) {
  if (el) nodeEls[i] = el as HTMLElement
}
const RAIL_X = 25        // 主时间轴节点中心 x（与 CSS 对应）
const OFFSET = 12        // 第一条平行车道相对主轴的左偏移
const LANE_GAP = 9       // 相邻车道间距（更靠左）
const MAX_LANES = 2      // 最多平行车道数，超出则退化重叠
const ARC = 8            // 弧线半径
interface Connector { d: string; color: string }
const connectors = ref<Connector[]>([])

function recomputeConnectors() {
  const wrap = timelineEl.value
  const tl = timeline.value
  if (!wrap || !tl.length) { connectors.value = []; return }
  const base = wrap.getBoundingClientRect()

  // 1. 收集每段连线的垂直区间
  const segs: { yTop: number; yBot: number; color: string }[] = []
  tl.forEach((origin, oi) => {
    if (!isPending(origin.status) || !origin.id) return
    const fb = repliedMap.value[origin.id]
    if (!fb) return
    const fi = tl.findIndex((x) => x === fb)
    if (fi < 0) return
    const oEl = nodeEls[oi]
    const fEl = nodeEls[fi]
    if (!oEl || !fEl) return
    const oR = oEl.getBoundingClientRect()
    const fR = fEl.getBoundingClientRect()
    const y1 = oR.top - base.top + oR.height / 2
    const y2 = fR.top - base.top + fR.height / 2
    const [yTop, yBot] = y1 <= y2 ? [y1, y2] : [y2, y1]
    segs.push({ yTop, yBot, color: progressColor(origin.status) })
  })

  // 2. 车道分配：按起点升序，放入第一个不与已占用段重叠的车道；
  //    车道用满（MAX_LANES）则退化到结束最早的车道（允许重叠）。
  segs.sort((a, b) => a.yTop - b.yTop)
  const laneEnd: number[] = []
  const list: Connector[] = []
  for (const s of segs) {
    let lane = laneEnd.findIndex((end) => end <= s.yTop)
    if (lane === -1) {
      if (laneEnd.length < MAX_LANES) {
        lane = laneEnd.length
        laneEnd.push(s.yBot)
      } else {
        // 退化：选当前结束最早的车道重叠使用
        lane = laneEnd.reduce((mi, end, i, arr) => (end < arr[mi] ? i : mi), 0)
        laneEnd[lane] = Math.max(laneEnd[lane], s.yBot)
      }
    } else {
      laneEnd[lane] = s.yBot
    }
    const px = RAIL_X - OFFSET - lane * LANE_GAP
    // 从上方节点弧出 → 平行虚线下行 → 弧入下方节点
    const d = [
      `M ${RAIL_X} ${s.yTop}`,
      `C ${RAIL_X - ARC} ${s.yTop}, ${px} ${s.yTop}, ${px} ${s.yTop + ARC}`,
      `L ${px} ${s.yBot - ARC}`,
      `C ${px} ${s.yBot}, ${RAIL_X - ARC} ${s.yBot}, ${RAIL_X} ${s.yBot}`,
    ].join(' ')
    list.push({ d, color: s.color })
  }
  connectors.value = list
}

let ro: ResizeObserver | null = null
function observeTimeline() {
  if (ro) { ro.disconnect(); ro = null }
  if (timelineEl.value && typeof ResizeObserver !== 'undefined') {
    ro = new ResizeObserver(() => recomputeConnectors())
    ro.observe(timelineEl.value)
  }
}
watch([timeline, editingProgress], async () => {
  await nextTick()
  recomputeConnectors()
  observeTimeline()
})
watch(() => props.visible, async (v) => {
  if (!v) return
  await nextTick()
  recomputeConnectors()
  observeTimeline()
})

function nowStr(): string {
  const d = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

function todayStr(): string {
  return nowStr().slice(0, 10)
}

/* 日历禁用未来日期（晚于今天的整天不可选） */
function disabledFutureDate(date: Date): boolean {
  const today = new Date()
  today.setHours(23, 59, 59, 999)
  return date.getTime() > today.getTime()
}

/* 进展时间是否晚于当前时刻（精确到分钟）。'time' 格式为 'YYYY-MM-DD HH:mm' */
function isFutureTime(time?: string): boolean {
  if (!time) return false
  const t = new Date(time.replace(' ', 'T')).getTime()
  if (Number.isNaN(t)) return false
  return t > Date.now()
}

/* 草稿中存在内容的进展是否含未来时间，返回第一条违规的内容片段（用于提示），无则返回 null */
function findFutureProgress(): string | null {
  const bad = progressDraft.value.find((e) => (e.content || '').trim() && isFutureTime(e.time))
  if (!bad) return null
  const snippet = (bad.content || '').trim().slice(0, 12)
  return snippet || (bad.time || '')
}

function blankProject(): Project {
  return {
    id: 0, name: '', record_date: todayStr(), content: null,
    status: 'planned' as ProjectStatus, urgency: 'medium' as ProjectUrgency,
    department: null, owner_name: null, related_name: null, completion: 0, is_long_term: false,
    estimated_end_date: null, actual_end_date: null, progress_log: null,
    version: 1, created_at: '', updated_at: '',
  }
}

function enterProgressEdit() {
  if (!local.value) return
  // 深拷贝以保留 annotations，并按更新时间升序排列（渲染时经 draftView 倒序为「上新下旧」，与展示态一致）
  progressDraft.value = JSON.parse(JSON.stringify(local.value.progress_log ?? []))
  progressDraft.value.sort(byTime)
  editingProgress.value = true
}
/* 进展「取消」：放弃未保存的草稿并退出编辑态（重新从 local 同步以备下次进入） */
function cancelProgressEdit() {
  editingProgress.value = false
  progressDraft.value = JSON.parse(JSON.stringify(local.value?.progress_log ?? []))
}
function addRow() {
  const entry: ProgressEntry = { id: genId(), time: nowStr(), content: '', status: '正常' }
  if (meeting.active) {
    entry.meeting_session = meeting.currentCount  // 持久化：标记该记录所属周会次数
    entry._isNew = true                           // 临时标记：本次会话新增，用于显示"周会记录："标签
  }
  progressDraft.value.push(entry)
}
/* 对未结束事件添加一条反馈：紧随其后插入，继承状况、reply_to 指向原事件 */
function addFeedback(i: number) {
  const origin = progressDraft.value[i]
  if (!origin.id) origin.id = genId()
  progressDraft.value.splice(i + 1, 0, {
    id: genId(),
    time: nowStr(),
    content: '',
    status: origin.status,
    reply_to: origin.id,
  })
}
/* 草稿中某未结束事件是否已有反馈（编辑态据此隐藏"反馈"按钮） */
function draftHasReply(e: ProgressEntry): boolean {
  return !!e.id && progressDraft.value.some((x) => x.reply_to === e.id)
}
function removeRow(i: number) {
  progressDraft.value.splice(i, 1)
}

/* 清洗草稿为可保存的 progress_log：补 id、保留 meeting_session/reply_to/annotations/attachments */
function cleanDraft(): ProgressEntry[] {
  return progressDraft.value
    .filter((e) => (e.content || '').trim())
    .map((e) => {
      const out: ProgressEntry = {
        id: e.id || genId(),
        time: e.time || nowStr(),
        content: e.content || '',
        status: e.status || '正常',
      }
      if (e.meeting_session != null) out.meeting_session = e.meeting_session
      if (e.reply_to) out.reply_to = e.reply_to
      if (e.annotations) out.annotations = e.annotations
      if (e.attachments) out.attachments = e.attachments
      return out
    })
}

async function commitProgress() {
  if (props.createMode) return
  if (!editingProgress.value || !local.value) return
  // 校验：进展时间不能晚于当前时刻
  const future = findFutureProgress()
  if (future) {
    ElMessage.error(`进展「${future}」的更新时间晚于当前时间，请修正后再保存`)
    return // 保持编辑态，不退出
  }
  editingProgress.value = false
  const cleaned = cleanDraft()
  // 无变化则不请求
  if (JSON.stringify(cleaned) === JSON.stringify(local.value.progress_log ?? [])) return
  try {
    const updated = await projectApi.update(
      local.value.id,
      { progress_log: cleaned, version: local.value.version } as Partial<Project>,
    )
    local.value = updated
    emit('updated')
  } catch (err) {
    if (isConflict(err)) {
      await mergeDraftOnConflict()
    } else {
      ElMessage.error('保存进展失败（需要管理员或项目经理权限）')
    }
  }
}

/* 进展保存遇乐观锁冲突（409）：拉取最新数据，把「我新增的条目」并入最新进展重建草稿并恢复编辑态，
   双方的新增都不丢；对既有条目的修改以服务端最新为准。
   条目键：优先 id；无 id 的历史条目用「时间|内容」兜底，避免并集时重复 */
async function mergeDraftOnConflict() {
  if (!local.value) return
  try {
    const fresh = await projectApi.get(local.value.id)
    const latest = fresh.progress_log ?? []
    const keyOf = (e: ProgressEntry) => e.id || `${e.time}|${e.content}`
    const knownKeys = new Set(latest.map(keyOf))
    // 我的新增 = 草稿中有内容、且键不存在于最新进展中的条目
    const mine = progressDraft.value.filter(
      (e) => (e.content || '').trim() && !knownKeys.has(keyOf(e)),
    )
    local.value = fresh
    progressDraft.value = JSON.parse(JSON.stringify([...latest, ...mine]))
    progressDraft.value.sort(byTime)
    editingProgress.value = true   // 恢复编辑态，待用户核对后重新保存
    ElMessage.warning('项目进展已被他人更新，已合并最新内容与您的新增记录，请核对后重新保存')
  } catch {
    ElMessage.error('项目已被他人修改，请刷新页面后重试')
  }
}

// 点击进展区域以外（且不在弹层内）时结束编辑
function onDocClick(e: MouseEvent) {
  if (!editingProgress.value) return
  const t = e.target as HTMLElement
  if (progressWrap.value?.contains(t)) return
  // 弹层（下拉、日期选择、对话框、消息提示）内的点击不触发退出
  // 注意：用 .el-overlay-dialog 而非 .el-overlay，后者也匹配抽屉自身遮罩会导致无法退出
  if (t.closest('.el-popper, .el-select-dropdown, .el-picker-panel, .el-picker__popper, .el-dialog, .el-overlay-dialog, .el-message-box, .el-message')) return
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
  // 初始化本地快照：会议页等「visible 恒 true、挂载时 project 已有值」的场景下，
  // 不会触发 visible/project 的 watch，需在此主动同步一次，否则 local 为 null、内容空白
  if (props.project || props.createMode) sync()
  loadDepartments()
  loadManagers()
  nextTick(() => { recomputeConnectors(); observeTimeline() })
})
onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick, true)
  if (ro) ro.disconnect()
})

/* 供壳在关闭前调用：执行未来时间校验 + 提交进展。
   返回 true=允许关闭，false=有未来时间，阻止关闭。 */
function flushBeforeClose(): boolean {
  if (!props.createMode && editingProgress.value) {
    // 存在未来时间的进展时，阻止关闭，提示修正
    if (findFutureProgress()) {
      ElMessage.error('存在更新时间晚于当前时间的进展记录，请修正后再关闭')
      return false
    }
    commitProgress()
  }
  return true
}

defineExpose({ flushBeforeClose })

/* ---------- 批注功能 ---------- */
const annotationDialog = reactive({
  visible: false,
  mode: 'annotation' as 'annotation' | 'reply',
  content: '',
  targetEntry: null as ProgressEntry | null,
  targetAnnotation: null as Annotation | null,
})

function genAnnotationId(): string {
  return `ann-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function nowISOStr(): string {
  return new Date().toISOString().slice(0, 19).replace('T', ' ')
}

function onProgressContextMenu(event: MouseEvent, entry: ProgressEntry) {
  event.preventDefault()
  annotationDialog.mode = 'annotation'
  annotationDialog.targetEntry = entry
  annotationDialog.targetAnnotation = null
  annotationDialog.content = ''
  annotationDialog.visible = true
}

function onAnnotationContextMenu(event: MouseEvent, entry: ProgressEntry, annotation: Annotation) {
  event.preventDefault()
  annotationDialog.mode = 'reply'
  annotationDialog.targetEntry = entry
  annotationDialog.targetAnnotation = annotation
  annotationDialog.content = ''
  annotationDialog.visible = true
}

async function saveAnnotation() {
  if (!annotationDialog.content.trim()) {
    ElMessage.warning('请输入批注内容')
    return
  }
  if (!annotationAuthor.value) {
    ElMessage.warning('无法获取当前用户信息')
    return
  }
  if (!local.value || !annotationDialog.targetEntry) return

  const entry = annotationDialog.targetEntry
  // 深拷贝 progress_log，避免直接修改引用
  const log = JSON.parse(JSON.stringify(local.value.progress_log ?? []))
  const entryIndex = log.findIndex((e: ProgressEntry) => e.id === entry.id)
  if (entryIndex === -1) return

  if (annotationDialog.mode === 'annotation') {
    // 添加批注
    const newAnnotation: Annotation = {
      id: genAnnotationId(),
      author_name: annotationAuthor.value,
      content: annotationDialog.content.trim(),
      created_at: nowISOStr(),
      replies: [],
    }
    if (!log[entryIndex].annotations) log[entryIndex].annotations = []
    log[entryIndex].annotations!.push(newAnnotation)
  } else {
    // 添加回复
    const ann = annotationDialog.targetAnnotation
    if (!ann) return
    const annIndex = (log[entryIndex].annotations ?? []).findIndex((a: Annotation) => a.id === ann.id)
    if (annIndex === -1) return
    const newReply: AnnotationReply = {
      id: genAnnotationId(),
      author_name: annotationAuthor.value,
      content: annotationDialog.content.trim(),
      created_at: nowISOStr(),
    }
    if (!log[entryIndex].annotations![annIndex].replies) log[entryIndex].annotations![annIndex].replies = []
    log[entryIndex].annotations![annIndex].replies!.push(newReply)
  }

  // 保存到后端
  try {
    const updated = await projectApi.update(
      local.value.id,
      { progress_log: log, version: local.value.version } as Partial<Project>,
    )
    local.value = updated
    emit('updated')
    annotationDialog.visible = false
    ElMessage.success(annotationDialog.mode === 'annotation' ? '批注已添加' : '回复已添加')
  } catch (err) {
    if (isConflict(err)) {
      // 冲突：刷新最新数据；对话框与已输入内容保留，再点确定即基于最新数据重新追加
      await refreshLocal()
      ElMessage.warning('项目已被他人更新，已刷新，请再次点击确定提交')
    } else {
      ElMessage.error('保存失败（需要管理员或项目经理权限）')
    }
  }
}

/* ---------- 文档附件功能 ---------- */
const attachDialog = reactive({
  visible: false,
  url: '',
  title: '',
  validating: false,
  error: '',
  targetIndex: -1,
})

function openAttachDialog(index: number) {
  attachDialog.targetIndex = index
  attachDialog.url = ''
  attachDialog.title = ''
  attachDialog.error = ''
  attachDialog.validating = false
  attachDialog.visible = true
}

function validateFeishuUrl(url: string): boolean {
  // 飞书文档链接格式：https://*.feishu.cn/docx/... 或 https://*.feishu.cn/docs/...
  const pattern = /^https:\/\/[a-zA-Z0-9-]+\.feishu\.cn\/(docx|docs|wiki|base|mindnote|file|drive)\/[a-zA-Z0-9_-]+/
  return pattern.test(url)
}

async function saveAttachment() {
  if (!attachDialog.url.trim()) {
    ElMessage.warning('请输入文档链接')
    return
  }

  const url = attachDialog.url.trim()

  // 验证链接格式
  if (!validateFeishuUrl(url)) {
    attachDialog.error = '链接格式不正确，请输入有效的飞书文档链接'
    return
  }

  attachDialog.validating = true
  attachDialog.error = ''

  // 简单验证：检查 URL 是否可访问（HEAD 请求）
  try {
    await fetch(url, { method: 'HEAD', mode: 'no-cors' })
    // no-cors 模式下无法读取响应状态，只要不抛错就认为链接有效
  } catch (err) {
    // fetch 失败可能是跨域或网络问题，但链接格式正确就允许添加
    console.warn('文档链接验证警告:', err)
  }

  attachDialog.validating = false

  // 添加附件到草稿
  const newAttachment: DocumentAttachment = {
    url,
    title: attachDialog.title.trim() || null,
    added_at: nowISOStr(),
  }

  if (!progressDraft.value[attachDialog.targetIndex].attachments) {
    progressDraft.value[attachDialog.targetIndex].attachments = []
  }
  progressDraft.value[attachDialog.targetIndex].attachments!.push(newAttachment)

  attachDialog.visible = false
  ElMessage.success('文档已添加')
}

function removeAttachment(entryIndex: number, attachIndex: number) {
  progressDraft.value[entryIndex].attachments?.splice(attachIndex, 1)
}


</script>

<style scoped>
.detail { display: flex; flex-direction: column; gap: var(--sp-5); padding: var(--sp-2) 0; position: relative; }
.edit-btn-group { position: absolute; top: 42px; right: 0; z-index: 2; display: flex; align-items: center; gap: 8px; }
.edit-btn { font-size: 16px; }
/* 记录时间：作为徽章行的普通 flex 子项，跟在状态/优先级之后 */
.record-time { font-size: 12px; color: var(--c-ink-3); }
.long-term-text { font-weight: 700; color: var(--c-accent); font-size: 14px; }
.mini-label { font-size: 12px; color: var(--c-ink-3); margin-bottom: 4px; }

.d-head { border-left: 3px solid var(--bar); padding-left: var(--sp-3); padding-right: 124px; }
.d-title-row { display: flex; align-items: center; gap: var(--sp-2); margin-bottom: var(--sp-2); }
.req { color: var(--c-status-overdue); margin-left: 2px; }
.d-title { font-family: var(--font-display); font-size: 21px; font-weight: 700; }
.d-title-input { max-width: 420px; }
.edit-ico { cursor: pointer; color: var(--c-ink-3); font-size: 18px; }
.edit-ico:hover { color: var(--c-accent); }
.d-badges { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; }
.badge { font-weight: 600; font-size: 12px; padding: 2px 10px; border-radius: var(--r-sm); }
.badge.overdue { color: var(--c-status-overdue); background: var(--c-status-overdue-soft); }

.brief { color: var(--c-ink-2); line-height: 1.6; font-size: 14px; }
/* head-row 默认透明（抽屉：简要说明与完成度仍各占一行）；会议页改为一排 */
.head-row { display: contents; }

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

/* 详情区按钮统一配色（抽屉 + 会议页共用同组件，自动同步）：
   蓝=编辑 / 琥珀=保存·创建 / 深红=删除 */
.btn-blue { background: #1a73e8; border-color: #1a73e8; color: #fff; }
.btn-blue:hover, .btn-blue:focus { background: #1763c8; border-color: #1763c8; color: #fff; }
.btn-amber { background: #f59e0b; border-color: #f59e0b; color: #fff; }
.btn-amber:hover, .btn-amber:focus { background: #d98c08; border-color: #d98c08; color: #fff; }
.btn-delete-deep { background: #c0392b; border-color: #c0392b; color: #fff; }
.btn-delete-deep:hover, .btn-delete-deep:focus { background: #a5311f; border-color: #a5311f; color: #fff; }
/* 进展「编辑/保存」按钮：在 baseline 对齐的标题行中居中 */
.pg-toggle-btn { align-self: center; }

/* 进展 */
.progress-block { border-top: 1px solid var(--c-border); padding-top: var(--sp-4); }
.prog-title { display: flex; align-items: baseline; gap: var(--sp-2); margin-bottom: var(--sp-3); }
.stalled-tag { font-size: 13px; white-space: nowrap; margin-left: var(--sp-2); }
.hint { font-size: 12px; margin-left: auto; }
.stalled-banner {
  text-align: center; font-style: italic; font-weight: 700; font-size: 17px;
  color: #c0c4cc; letter-spacing: 1px; margin-top: var(--sp-4);
}
.stalled-banner-days { font-weight: 800; font-style: italic; }

.prog-table { width: 100%; border-collapse: collapse; }
/* 「添加一条」移到表格上方后，与表格留出间距 */
.add-row-btn { margin-bottom: 6px; }
.prog-table th, .prog-table td { border: 1px solid var(--c-border); padding: 6px; vertical-align: top; text-align: left; }
.prog-table th { background: var(--c-surface-2); font-size: 12px; color: var(--c-ink-2); font-weight: 600; }
.empty-row { text-align: center; padding: var(--sp-3); }
.row-del { cursor: pointer; color: var(--c-ink-3); }
.row-del:hover { color: var(--c-status-overdue); }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }

/* 展示态时间线容器：只读（编辑通过上方「编辑」按钮进入，不再点击区域进入） */
.prog-view { border: 1px dashed transparent; border-radius: var(--r-md); padding: var(--sp-2); }
.tl-empty { padding: var(--sp-4); text-align: center; font-size: 13px; }

.timeline { position: relative; padding-left: 40px; }
.timeline::before {
  content: ''; position: absolute; left: 24px; top: 4px; bottom: 4px;
  width: 2px; background: var(--c-border);
}
/* 反馈连线 SVG 层：在主轴与节点之间，节点中心 x=25，平行车道在其左侧错开 */
.tl-svg {
  position: absolute; left: 0; top: 0; width: 100%; height: 100%;
  overflow: visible; pointer-events: none; z-index: 1;
}
.tl-item { position: relative; padding-bottom: var(--sp-4); }
.tl-item:last-child { padding-bottom: 0; }
.tl-node {
  position: absolute; left: -21px; top: 3px;
  width: 12px; height: 12px; border-radius: 50%;
  z-index: 2;
}
.tl-node.solid {
  border: 2px solid var(--c-surface); box-shadow: 0 0 0 1px var(--c-border);
}
.tl-node.hollow {
  background: var(--c-surface);
  border: 2px solid var(--nc);
  box-shadow: 0 0 0 2px var(--c-surface);
}
.tl-node.hollow.flashing { animation: tl-flash 1.1s ease-in-out infinite; }
@keyframes tl-flash {
  0%, 100% { box-shadow: 0 0 0 2px var(--c-surface), 0 0 0 2px transparent; opacity: 1; }
  50% { box-shadow: 0 0 0 2px var(--c-surface), 0 0 0 6px color-mix(in srgb, var(--nc) 35%, transparent); opacity: 0.6; }
}
.tl-meta { display: flex; align-items: center; gap: var(--sp-3); margin-bottom: 2px; }
.tl-time { font-size: 12px; color: var(--c-ink-3); }
.tl-status { font-size: 12px; font-weight: 600; }
.tl-content { font-size: 14px; color: var(--c-ink); line-height: 1.5; white-space: pre-wrap; }
/* 周会横幅：绝对定位到编辑按钮左侧、与按钮等高对齐 */
.meeting-banner { position: absolute; top: 42px; right: 132px; height: 40px; display: flex; align-items: center; color: #1a73e8; font-size: 18px; font-weight: 700; letter-spacing: 0.5px; z-index: 2; }
.content-cell { display: flex; align-items: flex-start; gap: 4px; }
.meeting-tag { color: #1a73e8; font-weight: 600; font-size: 13px; white-space: nowrap; padding-top: 6px; }
.feedback-tag { color: #1a73e8; font-weight: 600; font-size: 13px; white-space: nowrap; padding-top: 6px; }
.feedback-btn { flex-shrink: 0; padding: 0 6px; }
.attach-btn { flex-shrink: 0; padding: 0 6px; }
.meeting-prefix { color: #1a73e8; font-weight: 700; }

/* 文档附件样式 */
.edit-attachments { margin-top: var(--sp-2); display: flex; flex-direction: column; gap: 4px; }
.edit-attach-item {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 8px; background: var(--c-surface-2); border-radius: var(--r-sm);
}
.attach-icon { color: #1a73e8; font-size: 14px; }
.attach-link {
  flex: 1; font-size: 12px; color: #1a73e8; text-decoration: none;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.attach-link:hover { text-decoration: underline; }
.attach-remove { cursor: pointer; color: var(--c-ink-3); font-size: 14px; }
.attach-remove:hover { color: var(--c-status-overdue); }

.tl-attachments { margin-top: var(--sp-2); display: flex; flex-direction: column; gap: 4px; }
.tl-attach-item {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 10px; background: var(--c-surface-2); border-radius: var(--r-sm);
  border-left: 2px solid #1a73e8;
}

/* 批注样式 */
.annotations { margin-top: var(--sp-3); display: flex; flex-direction: column; gap: var(--sp-2); }
.annotation {
  background: var(--c-surface-2); border-left: 3px solid #1a73e8;
  padding: var(--sp-2) var(--sp-3); border-radius: var(--r-sm);
  cursor: context-menu;
}
.annotation:hover { background: var(--c-surface-3); }
.ann-header { display: flex; align-items: center; gap: var(--sp-2); margin-bottom: 4px; }
.ann-author { font-weight: 600; font-size: 13px; color: var(--c-ink); }
.ann-time { font-size: 11px; color: var(--c-ink-3); }
.ann-content { font-size: 13px; color: var(--c-ink-2); line-height: 1.5; white-space: pre-wrap; }
.ann-replies { margin-top: var(--sp-2); padding-left: var(--sp-3); display: flex; flex-direction: column; gap: var(--sp-2); }
.ann-reply {
  background: var(--c-canvas); padding: var(--sp-2);
  border-radius: var(--r-sm); border-left: 2px solid var(--c-border);
}
.reply-header { display: flex; align-items: center; gap: var(--sp-2); margin-bottom: 2px; }
.reply-author { font-weight: 600; font-size: 12px; color: var(--c-ink-2); }
.reply-time { font-size: 11px; color: var(--c-ink-3); }
.reply-content { font-size: 12px; color: var(--c-ink-2); line-height: 1.4; white-space: pre-wrap; }

/* 历史修改记录 tab */
.detail-tabs { margin-top: var(--sp-2); }
.history-block { min-height: 120px; max-height: 52vh; overflow-y: auto; padding: var(--sp-1) 0; }
.hist-list { display: flex; flex-direction: column; }
.hist-row {
  display: flex; align-items: baseline; gap: var(--sp-2);
  padding: var(--sp-2) 0; border-bottom: 1px solid var(--c-border); font-size: 13px;
}
.hist-user { flex-shrink: 0; font-weight: 600; color: #1a73e8; }
.hist-time { flex-shrink: 0; font-size: 12px; color: var(--c-ink-3); }
.hist-desc { color: var(--c-ink); line-height: 1.5; word-break: break-all; }

/* ---- 会议汇报页布局变体：页头信息固定、进展区滚动、占满容器高度 ---- */
.layout-meeting { height: 100%; }
.layout-meeting .detail { height: 100%; min-height: 0; gap: var(--sp-3); }
/* 页头信息区固定不滚动 */
.layout-meeting .d-head,
.layout-meeting .brief-block,
.layout-meeting .prog-block,
.layout-meeting .d-fields,
.layout-meeting .edit-actions { flex: none; }
/* tab 区域占据剩余高度 */
.layout-meeting .detail-tabs { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.layout-meeting .detail-tabs :deep(.el-tabs__content) { flex: 1; min-height: 0; overflow-y: auto; }
.layout-meeting .history-block { max-height: none; }

/* 会议页大屏：详情区文字整体加大两号（仅 layout-meeting，不影响抽屉场景） */
.layout-meeting .d-title { font-size: 25px; }
.layout-meeting .brief { font-size: 16px; }
.layout-meeting .mini-label { font-size: 16px; }
.layout-meeting .badge { font-size: 16px; }
.layout-meeting .record-time { font-size: 16px; }
.layout-meeting .long-term-text { font-size: 18px; }
.layout-meeting .f dt,
.layout-meeting .f dd { font-size: 17px; }
.layout-meeting .pct,
.layout-meeting .num { font-size: 18px; }
.layout-meeting .hint { font-size: 15px; }
.layout-meeting .stalled-tag { font-size: 17px; }
.layout-meeting .tl-time { font-size: 16px; }
.layout-meeting .tl-status { font-size: 16px; }
.layout-meeting .tl-content { font-size: 18px; }
.layout-meeting .ann-author { font-size: 17px; }
.layout-meeting .ann-time { font-size: 15px; }
.layout-meeting .ann-content { font-size: 17px; }
.layout-meeting .reply-author,
.layout-meeting .reply-time,
.layout-meeting .reply-content { font-size: 16px; }
.layout-meeting .hist-user,
.layout-meeting .hist-time,
.layout-meeting .hist-desc { font-size: 17px; }
.layout-meeting .prog-table th,
.layout-meeting .prog-table td { font-size: 16px; }
/* 进展编辑态：输入框文字（进展内容/时间/状态）放大两号 */
.layout-meeting .prog-edit :deep(.el-textarea__inner),
.layout-meeting .prog-edit :deep(.el-input__inner) { font-size: 17px; }
/* 状态下拉选项 + 「反馈/文档」按钮 + 标签 同步放大 */
.layout-meeting .prog-edit :deep(.el-select__placeholder),
.layout-meeting .prog-edit :deep(.el-button) { font-size: 15px; }
.layout-meeting .prog-edit .feedback-tag,
.layout-meeting .prog-edit .meeting-tag { font-size: 15px; }
.layout-meeting .prog-edit .attach-link { font-size: 15px; }
.layout-meeting :deep(.el-tabs__item) { font-size: 17px; }

/* 压缩信息区：简要说明跨前两列，完成度落第三列（与下方「相关人」列左对齐）；字段三列两排 */
.layout-meeting .head-row { display: grid; grid-template-columns: repeat(3, 1fr); column-gap: var(--sp-5); align-items: flex-start; }
.layout-meeting .brief-block { grid-column: 1 / 3; min-width: 0; display: flex; align-items: baseline; gap: 8px; }
.layout-meeting .brief-block .mini-label { flex: none; margin-bottom: 0; }
.layout-meeting .prog-block { grid-column: 3 / 4; width: auto; }
.layout-meeting .d-fields { grid-template-columns: repeat(3, 1fr); }
/* 第一排：部门 / 负责人 / 相关人；第二排：优先级 / 完成情况 / 截止日期
   （DOM 顺序为 部门,负责人,相关人,完成情况,优先级,截止日期，用 order 交换 4↔5） */
.layout-meeting .d-fields .f:nth-child(1) { order: 1; }
.layout-meeting .d-fields .f:nth-child(2) { order: 2; }
.layout-meeting .d-fields .f:nth-child(3) { order: 3; }
.layout-meeting .d-fields .f:nth-child(4) { order: 5; }
.layout-meeting .d-fields .f:nth-child(5) { order: 4; }
.layout-meeting .d-fields .f:nth-child(6) { order: 6; }
/* 字段标签不换行（完成情况/截止日期等 4 字标签放大后会折行） */
.layout-meeting .f dt { width: 76px; white-space: nowrap; }
/* 项目编辑按钮：缩小并上移，与项目名称高度对齐 */
.layout-meeting .edit-btn-group { top: 0; }
.layout-meeting .edit-btn { height: 34px; padding: 0 14px; font-size: 14px; }
</style>
