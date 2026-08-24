<template>
  <div class="page overview-page">
    <div class="page-head">
      <h1 class="page-title">项目总览</h1>
    </div>

    <div class="head-toolbar">
      <p class="muted">目前有 {{ trackingCount }} 个跟踪项目（除去已完成/取消），其中重要项目 {{ importantCount }} 个，高优先级项目 {{ highPriorityCount }} 个</p>
      <div class="head-actions">
        <el-autocomplete
          v-model="keyword"
          :fetch-suggestions="querySearch"
          placeholder="搜索项目 / 负责人 / 相关人 / 部门 / 进展…"
          clearable
          :prefix-icon="Search"
          :trigger-on-focus="false"
          value-key="value"
          style="width: 300px; margin-right: 60px"
          @select="onSelectSuggestion"
        >
          <template #default="{ item }">
            <div class="ac-item">
              <span class="ac-name">{{ item.value }}</span>
              <span v-if="item.meta" class="ac-meta">{{ item.meta }}</span>
            </div>
          </template>
        </el-autocomplete>
        <el-button text :icon="View" :disabled="!currentRow" @click="detailSelected">详情</el-button>
        <el-button text type="danger" :icon="Delete" :disabled="!currentRow" @click="removeSelected">删除</el-button>
        <el-dropdown trigger="click" @command="onAddCommand">
          <el-button text :icon="Plus">新增<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="project">新增项目</el-dropdown-item>
              <el-dropdown-item command="group">新增项目组</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <el-table
      ref="tableRef"
      v-loading="loading"
      :data="rows"
      stripe
      border
      size="default"
      row-key="id"
      :tree-props="{ children: 'children' }"
      :default-expand-all="!!keyword.trim()"
      height="100%"
      highlight-current-row
      :header-cell-style="headerCellStyle"
      :default-sort="{ prop: '', order: null }"
      style="width: 100%"
      @current-change="onCurrentChange"
      @row-dblclick="openDetail"
      @expand-change="onExpandChange"
      :row-class-name="rowClassName"
    >
      <el-table-column label="" width="38" align="center" class-name="signal-col">
        <template #default="{ row }">
          <el-tooltip v-if="row._hasRecentUpdate" :content="`近 3 天有更新：${row._lastStatus || '进展'}`" placement="top" effect="light">
            <span class="signal-dot" :style="{ background: row._lastStatusColor || '#52c41a' }" aria-label="近 3 天有更新"></span>
          </el-tooltip>
        </template>
      </el-table-column>

      <el-table-column prop="name" label="待办事项 / 项目名称" min-width="260">
        <template #default="{ row }">
          <span v-if="row.parent_id != null" class="child-branch" :class="{ last: row._isLastChild }"></span>
          <span
            v-if="row.is_group && row.children && row.children.length"
            class="tree-toggle" @click.stop="toggleRow(row)"
          >{{ isExpanded(row) ? '−' : '+' }}</span>
          <span v-else-if="row.parent_id == null" class="tree-toggle-spacer"></span>
          <span v-if="row.is_group" class="group-tag">组</span>
          <el-tooltip
            v-if="row.content"
            :content="row.content"
            placement="top" effect="light" popper-class="desc-tip"
          >
            <span class="link" :class="{ 'child-name': row.parent_id != null }" @click="openDetail(row)">{{ row.name }}</span>
          </el-tooltip>
          <span v-else class="link" :class="{ 'child-name': row.parent_id != null }" @click="openDetail(row)">{{ row.name }}</span>
          <el-button
            v-if="row.is_group"
            size="small" class="add-child-btn" :icon="Plus"
            @click.stop="openCreateChild(row)"
          >子项</el-button>
        </template>
      </el-table-column>

      <el-table-column
        prop="department" label="部门" width="100" align="center"
        sortable :sort-method="sortDept"
        :filters="deptFilters" :filter-method="filterDept"
      >
        <template #default="{ row }">
          <span v-if="row.parent_id == null" :style="{ color: row._deptColor, fontWeight: row._deptShort ? 600 : 400 }">
            {{ row._deptShort || '—' }}
          </span>
          <span v-else class="child-dept">{{ row._deptShort || '—' }}</span>
        </template>
      </el-table-column>

      <el-table-column
        prop="status" label="完成情况" width="124" align="center"
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

      <el-table-column
        label="项目进展" min-width="380"
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
            <span class="progress-cell">
              <span class="prog-main"><span v-if="row._lastStatus" class="prog-status" :style="{ color: row._lastStatusColor }">【{{ row._lastStatus }}】</span>{{ row._lastProgress || '—' }}</span>
              <span
                v-for="m in row._pendingMarks" :key="m.status"
                class="pending-mark" :style="{ color: m.color }" :title="m.status + '（未反馈）'"
              >?</span>
              <span v-if="row._stalledColor" class="stalled" :style="{ color: row._stalledColor, fontWeight: row._stalledBold ? 700 : 400 }">⏱{{ row._stalledDays }}</span>
            </span>
          </el-tooltip>
          <span v-else class="no-progress">- 无进展记录 -</span>
        </template>
      </el-table-column>

      <el-table-column
        prop="owner_name" label="负责人" width="116" align="center"
        sortable :sort-method="sortOwner"
        :filters="ownerFilters" :filter-method="filterOwner"
      >
        <template #default="{ row }">{{ row.owner_name || '—' }}</template>
      </el-table-column>

      <el-table-column
        prop="related_name" label="相关人" width="120" align="center" show-overflow-tooltip
      >
        <template #default="{ row }">{{ row.related_name || '—' }}</template>
      </el-table-column>

      <el-table-column
        prop="urgency" label="优先级" width="108" align="center"
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
            <div class="tbar"><div class="tbar-fill" :style="{ width: row.completion + '%', background: completionGradient(row.completion) }" /></div>
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
      :is-group="createIsGroup"
      :parent="createParent"
      :departments="deptValues"
      :owners="ownerValues"
      @updated="load"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, View, Delete, ArrowDown } from '@element-plus/icons-vue'
import { projectApi, departmentApi } from '@/api/resources'
import type { Project, ProjectStatus, ProjectUrgency, Department } from '@/types'
import {
  projectStatusLabel, projectStatusColor, urgencyLabel, urgencyColor,
  urgencyWeight, PROJECT_STATUS_ORDER, PROGRESS_STATUSES, PENDING_STATUSES, isOverdue, progressStatusColor,
  completionGradient,
} from '@/utils/labels'
import ProjectDetailDrawer from '@/components/ProjectDetailDrawer.vue'

const projects = ref<Project[]>([])
const departments = ref<Department[]>([])
const loading = ref(false)
const keyword = ref('')

/* 项目组展开：信号灯占据首列后，el-table 原生展开图标（锁在首列）被 CSS 隐藏，
   改由名称列的自定义 +/− 触发 toggleRowExpansion，展开态用 expandedIds 反查渲染 ± 号 */
const tableRef = ref()
const expandedIds = ref(new Set<number>())
function toggleRow(row: Project) { tableRef.value?.toggleRowExpansion(row) }
function onExpandChange(row: Project, expanded: boolean) {
  const s = new Set(expandedIds.value)
  if (expanded) s.add(row.id); else s.delete(row.id)
  expandedIds.value = s
}
const isExpanded = (row: Project) => (keyword.value.trim() ? true : expandedIds.value.has(row.id))
// 关键词切换会让 el-table 重置树展开态（default-expand-all），同步清空本地展开集
watch(keyword, () => { expandedIds.value = new Set() })

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

/* 汇总一个项目的全部可搜索文本：名称/说明/部门(全称+简称)/负责人/相关人/
   状态与优先级(中英)/全部进展(内容+状况)/全部批注与回复(内容+作者)。
   缓存到 WeakMap，避免每次按键重复拼接大字符串。 */
const _searchBlobCache = new WeakMap<Project, string>()
function projectSearchBlob(p: Project): string {
  const cached = _searchBlobCache.get(p)
  if (cached) return cached
  const parts: string[] = [
    p.name,
    p.content || '',
    p.department || '',
    getDepartmentShortName(p.department),
    p.owner_name || '',
    p.related_name || '',
    p.status, statusLabel(p.status),
    p.urgency, urgText(p.urgency),
  ]
  for (const e of (p.progress_log ?? [])) {
    parts.push(e.content || '', e.status || '')
    for (const a of (e.annotations ?? [])) {
      parts.push(a.content || '', a.author_name || '')
      for (const r of (a.replies ?? [])) {
        parts.push(r.content || '', r.author_name || '')
      }
    }
  }
  const blob = parts.join('\n').toLowerCase()
  _searchBlobCache.set(p, blob)
  return blob
}

/* 项目是否命中关键词（覆盖项目全部信息内容） */
function projectMatchesKeyword(p: Project, kw: string): boolean {
  if (!kw) return true
  return projectSearchBlob(p).includes(kw)
}

/* 命中位置标注：用于下拉候选副信息，说明匹配到哪类内容 */
function matchHint(p: Project, kw: string): string {
  if (!kw) return ''
  const inText = (s?: string | null) => (s || '').toLowerCase().includes(kw)
  if (inText(p.name)) return ''
  if (inText(p.owner_name)) return '负责人'
  if (inText(p.related_name)) return '相关人'
  if (inText(p.department) || getDepartmentShortName(p.department).toLowerCase().includes(kw)) return '部门'
  if (inText(p.content)) return '说明'
  for (const e of (p.progress_log ?? [])) {
    if (inText(e.content) || inText(e.status)) return '进展'
    for (const a of (e.annotations ?? [])) {
      if (inText(a.content) || inText(a.author_name)) return '批注'
      for (const r of (a.replies ?? [])) {
        if (inText(r.content) || inText(r.author_name)) return '批注'
      }
    }
  }
  return '其他'
}

/* 智能补齐搜索：覆盖项目全部信息内容，下拉候选含副信息 + 命中位置 */
interface SearchSuggestion { value: string; meta: string }
function querySearch(q: string, cb: (results: SearchSuggestion[]) => void) {
  const kw = (q || '').trim().toLowerCase()
  const matched = projects.value
    .filter((p) => projectMatchesKeyword(p, kw))
    .slice(0, 10)
    .map((p) => {
      const where = matchHint(p, kw)
      const baseParts = [getDepartmentShortName(p.department) || p.department, p.owner_name]
      // 命中相关人时，把相关人也带进副信息，便于用户看清匹配原因
      if (where === '相关人' && p.related_name) baseParts.push(`相关人:${p.related_name}`)
      const base = baseParts.filter(Boolean).join(' · ')
      return {
        value: p.name,
        meta: where ? `${base}　· 命中${where}` : base,
      }
    })
  cb(matched)
}

/* 选中候选：以项目名过滤表格并选中该行 */
function onSelectSuggestion(item: Record<string, unknown>) {
  keyword.value = String(item.value || '')
  const hit = projects.value.find((p) => p.name === item.value)
  if (hit) currentRow.value = hit
}

/* 表头：文字居中 + 黑色 */
const headerCellStyle = { textAlign: 'center' as const, color: 'var(--c-ink)', fontWeight: 600 }

/* 计算跟踪项目数量（排除已完成/取消；暂停项目仍计入） */
const trackingCount = computed(() => {
  return projects.value.filter(p => !['completed', 'cancelled'].includes(p.status)).length
})

/* 计算重要项目数量（优先级为 urgent，排除已完成/取消；暂停项目仍计入） */
const importantCount = computed(() => {
  return projects.value.filter(p =>
    p.urgency === 'urgent' && !['completed', 'cancelled'].includes(p.status)
  ).length
})

/* 计算高优先级项目数量（优先级为 high，排除已完成/取消；暂停项目仍计入） */
const highPriorityCount = computed(() => {
  return projects.value.filter(p =>
    p.urgency === 'high' && !['completed', 'cancelled'].includes(p.status)
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
/* 停滞分级：按最新进展距今天数映射颜色/加粗/严重 */
function stalledMetaOf(lastTime: string): { days: number; color: string; bold: boolean; critical: boolean } {
  const t = new Date(lastTime.replace(' ', 'T'))
  const days = Math.floor((Date.now() - t.getTime()) / 86400000)
  let color = ''
  let bold = false
  if (days <= 30) color = ''
  else if (days <= 40) color = '#9AA0A6'
  else if (days <= 50) color = '#E6B422'
  else if (days <= 60) color = '#E6A23C'
  else if (days <= 70) { color = '#FA8C16'; bold = true }
  else if (days <= 90) { color = '#F0492A'; bold = true }
  else { color = '#E5484D'; bold = true }
  return { days, color, bold, critical: days > 90 }
}

const rows = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  const sortFn = (a: Project, b: Project) =>
    cmpStr(getDepartmentShortName(a.department), getDepartmentShortName(b.department))
    || cmpStr(a.owner_name, b.owner_name)
    || (urgWeight(b.urgency) - urgWeight(a.urgency))
  // 子项目按父组分桶
  const childrenOf = new Map<number, Project[]>()
  for (const p of projects.value) {
    if (p.parent_id != null) {
      const arr = childrenOf.get(p.parent_id) ?? []
      arr.push(p)
      childrenOf.set(p.parent_id, arr)
    }
  }
  const tops = [...projects.value].filter((p) => p.parent_id == null).sort(sortFn)
  type Row = ReturnType<typeof enrichRow> & { children?: ReturnType<typeof enrichRow>[] }
  const out: Row[] = []
  for (const top of tops) {
    if (top.is_group) {
      const kids = [...(childrenOf.get(top.id) ?? [])].sort(sortFn)
      const groupMatch = projectMatchesKeyword(top, kw)
      const matchedKids = kw ? kids.filter((k) => projectMatchesKeyword(k, kw)) : kids
      // 关键词：组或任一子项目命中即保留（仿 MeetingReportTree）；组自身命中而子项目均未命中时仍展示全部子项目
      if (kw && !groupMatch && !matchedKids.length) continue
      const shownKids = kw ? (matchedKids.length ? matchedKids : kids) : kids
      out.push({
        ...enrichRow(top),
        children: shownKids.map((k, i) => ({ ...enrichRow(k), _isLastChild: i === shownKids.length - 1 })),
      })
    } else if (!kw || projectMatchesKeyword(top, kw)) {
      out.push(enrichRow(top))
    }
  }
  return out
})

/* 单行富化：进展/停滞/待办标记等（组与子项目、独立项目统一处理） */
function enrichRow(p: Project) {
  const log = [...(p.progress_log ?? [])].sort((a, b) => (a.time || '').localeCompare(b.time || ''))
  const lastTime = log.length ? (log[log.length - 1].time || '') : ''
  const stalled = lastTime ? stalledMetaOf(lastTime) : null
  // 未闭合 pending：pending 状态、非反馈本身（无 reply_to）、且其 id 未被任何 reply_to 引用
  const replied = new Set(log.filter((e) => e.reply_to).map((e) => e.reply_to))
  const openSet = new Set(
    log.filter((e) =>
      (PENDING_STATUSES as readonly string[]).includes(e.status)
      && !e.reply_to
      && !(e.id && replied.has(e.id)),
    ).map((e) => e.status),
  )
  const pendingMarks = (PENDING_STATUSES as readonly string[])
    .filter((s) => openSet.has(s))
    .map((s) => ({ status: s, color: progressColor(s) }))
  const last = log.length ? log[log.length - 1] : null
  let lastDisplayStatus = last ? (last.status || '') : ''
  let lastDisplayColor = lastDisplayStatus ? progressColor(lastDisplayStatus) : ''
  if (last) {
    if (last.reply_to) {
      const origin = log.find((e) => e.id === last.reply_to)
      lastDisplayStatus = '已反馈'
      lastDisplayColor = progressColor(origin?.status || last.status || '')
    } else if (
      (PENDING_STATUSES as readonly string[]).includes(last.status)
      && last.id && replied.has(last.id)
    ) {
      lastDisplayStatus = '已反馈'
      lastDisplayColor = progressColor(last.status)
    }
  }
  const hasRecentUpdate = lastTime ? (Date.now() - new Date(lastTime).getTime()) / 86400000 <= 3 : false
  return {
    ...p,
    _deptShort: getDepartmentShortName(p.department),
    _deptColor: getDepartmentColor(p.department),
    _hasProgress: log.length > 0,
    _hasRecentUpdate: hasRecentUpdate,
    _stalledDays: stalled?.days ?? null,
    _stalledColor: stalled?.color ?? '',
    _stalledBold: stalled?.bold ?? false,
    _stalledCritical: stalled?.critical ?? false,
    _pendingMarks: pendingMarks,
    _lastProgress: log.length ? (log[log.length - 1].content || '') : '',
    _lastStatus: lastDisplayStatus,
    _lastStatusColor: lastDisplayColor,
    _recentProgress: [...log].slice(-8),
    _hasMore: log.length > 8,
  }
}

function rowClassName({ row }: { row: { _stalledCritical?: boolean } }): string {
  return row._stalledCritical ? 'row-critical' : ''
}

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
const createIsGroup = ref(false)
const createParent = ref<Project | null>(null)
function openDetail(row: Project) {
  createMode.value = false
  createIsGroup.value = false
  createParent.value = null
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
  const msg = row.is_group
    ? `确定删除项目组「${row.name}」？将级联删除该组及其全部子项目（含各自的任务/风险），不可恢复。`
    : `确定删除项目「${row.name}」？此操作不可恢复。`
  try {
    await ElMessageBox.confirm(msg, '删除确认', { type: 'warning' })
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

/* 新增下拉：项目 / 项目组 */
function onAddCommand(cmd: 'project' | 'group') {
  createParent.value = null
  createIsGroup.value = cmd === 'group'
  createMode.value = true
  detailProject.value = null
  detailVisible.value = true
}

/* 组内新增子项目：预填父组属性（copy-on-create） */
function openCreateChild(group: Project) {
  createIsGroup.value = false
  createParent.value = group
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
/* 整页填满内容区、不随表体滚动；仅 el-table 表体内部滚动，表头与工具栏固定 */
.overview-page {
  height: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.overview-page .page-head,
.overview-page .head-toolbar,
.overview-page .footer-bar {
  flex-shrink: 0;
}
/* el-table 占据剩余高度，min-height:0 允许其在 flex 容器内收缩并触发内部滚动 */
.overview-page :deep(.el-table) {
  flex: 1;
  min-height: 0;
}
/* 信号灯占据首列后，el-table 原生展开图标（锁死首列）一律隐藏，
   展开/折叠改由名称列的 .tree-toggle 自定义 +/− 驱动 */
.overview-page :deep(.el-table__expand-icon) { display: none; }
.overview-page :deep(.el-table__placeholder) { display: none; }
.head-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--sp-3);
  margin-bottom: var(--sp-1);
}
.head-actions {
  display: flex;
  gap: 0;
  align-items: center;
}
.badge { font-weight: 600; font-size: 12px; padding: 2px 8px; border-radius: var(--r-sm); }
.urg { font-weight: 600; }
.link { color: var(--c-accent); cursor: pointer; font-weight: 500; }
.link:hover { text-decoration: underline; }
.group-tag {
  display: inline-block; font-size: 11px; font-weight: 700; color: #fff;
  background: var(--c-accent); border-radius: var(--r-sm); padding: 1px 6px; margin-right: 6px;
}
/* 名称列自定义展开开关：方框 +/− */
.tree-toggle {
  display: inline-block; width: 15px; height: 15px; line-height: 13px;
  margin-right: 6px; text-align: center; cursor: pointer; user-select: none;
  font-size: 14px; font-weight: 700; color: var(--c-accent);
  border: 1px solid var(--c-accent); border-radius: 3px; box-sizing: border-box;
  vertical-align: middle;
}
.tree-toggle-spacer { display: inline-block; width: 15px; margin-right: 6px; }
.add-child-btn {
  margin-left: 8px; padding: 1px 8px; height: auto; line-height: 18px;
  border: none; border-radius: 9px; background: var(--c-ink-3, #909399); color: #fff;
}
.add-child-btn:hover, .add-child-btn:focus { background: var(--c-ink-2, #606266); color: #fff; }

/* 子项目分支连线：├─ / └─（末位用 last），营造树状缩进层级 */
.child-branch {
  display: inline-block; width: 18px; height: 1em; margin-right: 4px; position: relative; vertical-align: middle;
}
.child-branch::before {
  content: ''; position: absolute; left: 4px; top: -8px; bottom: 50%;
  border-left: 1px solid var(--c-border-strong, #c0c4cc);
}
.child-branch::after {
  content: ''; position: absolute; left: 4px; top: 50%; width: 10px;
  border-top: 1px solid var(--c-border-strong, #c0c4cc);
}
.child-branch.last::before { bottom: 50%; }
.child-name { color: var(--c-ink-2); font-weight: 400; }
.child-dept { color: var(--c-ink-3, #909399); font-weight: 400; }

/* 子项目行（展开后）：淡蓝底、行高略减、无中间分隔线 */
.overview-page :deep(.el-table__row--level-1) td.el-table__cell {
  background: #f0f6ff;
  padding-top: 4px; padding-bottom: 4px;
  border-bottom: none;
}
.overview-page :deep(.el-table__row--level-1:hover) td.el-table__cell {
  background: #e6f0ff;
}
.progress-cell { display: flex; align-items: center; gap: 6px; }
.prog-main { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.prog-status { font-weight: 600; }
.pending-mark { flex-shrink: 0; font-weight: 800; font-size: 16px; line-height: 1; cursor: default; animation: pending-blink 1s ease-in-out infinite; }
@keyframes pending-blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.25; } }
.stalled { flex-shrink: 0; font-size: 13px; white-space: nowrap; }
.no-progress { color: var(--c-ink-3); font-size: 13px; }

.tbar { display: inline-block; width: 70px; height: 6px; background: var(--c-canvas); border-radius: 999px; overflow: hidden; vertical-align: middle; }
.tbar-fill { height: 100%; border-radius: 999px; }
.tpct { margin-left: var(--sp-2); font-size: 12px; color: var(--c-ink-2); }
.long-term-text { font-weight: 700; color: var(--c-accent); font-size: 13px; }
.overdue { color: var(--c-status-overdue); font-weight: 600; }

.footer-bar { margin-top: var(--sp-3); font-size: 13px; }
:deep(.el-table) { --el-table-border-color: var(--c-border); }
/* 停滞 >90 天：整行淡红背景（覆盖斑马纹） */
:deep(.el-table .row-critical td.el-table__cell) { background-color: #fdecec; }

/* 更新信号灯：3 天内有进展 → 颜色随最新进展状态（延迟=黄、待确认=粉、已反馈=绿等） */
.signal-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  /* background 由 :style 动态绑定到 row._lastStatusColor */
  box-shadow: 0 0 4px currentColor;
  opacity: 0.9;
}
</style>

<!-- 「说明」列 tooltip 样式：浅棕背景 + 黑字 + 合适尺寸。
     tooltip 通过 teleport 挂到 body，必须用非 scoped 全局样式才能命中。 -->
<style>
/* 智能补齐下拉项（teleport 到 body，需全局样式） */
.ac-item { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
.ac-item .ac-name { font-weight: 500; color: var(--c-ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ac-item .ac-meta { font-size: 12px; color: var(--c-ink-3); flex-shrink: 0; }

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
