<template>
  <div class="mr-tree">
    <div class="mr-search">
      <el-input v-model="keyword" placeholder="🔍 查找项目 / 负责人 / 部门" clearable size="small" class="mr-search-input" />
      <div class="mr-filter">
        <span class="mr-filter-label">不显示：</span>
        <el-checkbox-group v-model="store.hiddenStatuses" size="small" class="mr-filter-group">
          <el-checkbox label="completed">已完成</el-checkbox>
          <el-checkbox label="cancelled">已取消</el-checkbox>
          <el-checkbox label="paused">暂停</el-checkbox>
          <el-checkbox label="planned">待启动</el-checkbox>
        </el-checkbox-group>
      </div>
      <span class="mr-hint">⇅ 拖拽部门 / 组内拖拽个人 调整汇报顺序</span>
    </div>

    <div class="mr-scroll">
      <div
        v-for="(d, di) in filteredGroups"
        :key="d.dept"
        class="mr-dept"
        draggable="true"
        @dragstart="onDeptDragStart(di)"
        @dragover.prevent
        @drop="onDeptDrop(di)"
      >
        <!-- 点击部门名：展开/折叠该部门所有负责人的项目列表 -->
        <div class="mr-dept-head" :style="{ background: d.color ? `color-mix(in srgb, ${d.color} 16%, #fff)` : 'var(--c-surface-2, #f2f3f5)' }"
          @click="toggleDept(d)">
          <span class="caret">{{ deptHasExpanded(d) ? '▾' : '▸' }}</span>
          <span class="swatch" :style="{ background: d.color || 'var(--c-ink-3)' }"></span>
          <b>{{ d.dept }}</b>
        </div>

        <div
          v-for="(m, mi) in d.members"
          :key="m.name"
          class="mr-member"
          draggable="true"
          @dragstart.stop="onMemberDragStart(d.dept, mi)"
          @dragover.prevent
          @drop.stop="onMemberDrop(d.dept, mi)"
        >
          <!-- 点击负责人名：展开/折叠他的项目列表 -->
          <div class="mr-member-head" @click="toggleMember(d.dept, m.name)">
            <span class="caret">{{ isMemberExpanded(d.dept, m.name) ? '▾' : '▸' }}</span>
            {{ m.name }} ({{ m.projects.length }})
          </div>
          <!-- 展开规则：搜索时全展开；否则取手动状态，默认仅当前汇报部门展开 -->
          <template v-if="isMemberExpanded(d.dept, m.name)">
            <div
              v-for="p in m.projects"
              :key="p.id"
              class="mr-proj"
              :class="{ cur: p.id === store.currentProjectId }"
              @click="store.selectProject(p.id)"
            >
              <span class="mr-pst" :style="{ color: statusColor(p.status) }">【{{ statusLabel(p.status) }}】</span>{{ p.name }}
            </div>
          </template>
        </div>
      </div>
      <div v-if="!filteredGroups.length" class="mr-empty">无匹配项目</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElInput, ElCheckbox, ElCheckboxGroup } from 'element-plus'
import { useMeetingReportStore } from '@/stores/meetingReport'
import { projectStatusLabel, projectStatusColor } from '@/utils/labels'
import type { MeetingReportOrder, ProjectStatus } from '@/types'

const store = useMeetingReportStore()
const keyword = ref('')

/* 项目状态中文标签 / 颜色 */
const statusLabel = (s: ProjectStatus) => projectStatusLabel[s]
const statusColor = (s: ProjectStatus) => projectStatusColor[s]

/* 当前汇报部门：默认仅该部门在左树展开项目，其他部门折叠到负责人 */
const currentDept = computed(() => store.presenters[store.currentPresenterIndex]?.dept ?? null)

/* 手动展开/折叠状态：key=`部门|负责人`，记录用户点击的结果；未设置的按默认（当前汇报部门展开）显示 */
const manualExpand = ref<Record<string, boolean>>({})
const memberKey = (dept: string, member: string) => `${dept}|${member}`

/* 某负责人项目列表是否展开：搜索时强制全展开；其次取手动状态；默认仅当前汇报部门展开 */
function isMemberExpanded(dept: string, member: string): boolean {
  if (keyword.value.trim()) return true
  const key = memberKey(dept, member)
  if (key in manualExpand.value) return manualExpand.value[key]
  return dept === currentDept.value
}
/* 部门下是否有任一负责人展开（用于部门折叠图标 ▾/▸ 与整组切换判断） */
function deptHasExpanded(d: { dept: string; members: { name: string }[] }): boolean {
  return d.members.some((m) => isMemberExpanded(d.dept, m.name))
}
/* 点击负责人名：翻转他的项目列表展开/折叠 */
function toggleMember(dept: string, member: string) {
  manualExpand.value[memberKey(dept, member)] = !isMemberExpanded(dept, member)
}
/* 点击部门名：该部门有任一展开→全部折叠；否则→全部展开 */
function toggleDept(d: { dept: string; members: { name: string }[] }) {
  const expand = !deptHasExpanded(d)
  for (const m of d.members) manualExpand.value[memberKey(d.dept, m.name)] = expand
}

/* 关键词过滤：命中项目名/负责人/部门即保留该项目；保持分组结构 */
const filteredGroups = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return store.grouped
  return store.grouped
    .map((d) => ({
      ...d,
      members: d.members
        .map((m) => ({
          ...m,
          projects: m.projects.filter((p) =>
            [p.name, p.owner_name, p.department].some((s) => (s || '').toLowerCase().includes(kw)),
          ),
        }))
        .filter((m) => m.projects.length > 0),
    }))
    .filter((d) => d.members.length > 0)
})

/* ---- 部门级拖拽：重排 order.departments ---- */
const dragDept = ref<number | null>(null)
function onDeptDragStart(i: number) { dragDept.value = i }
function onDeptDrop(target: number) {
  const from = dragDept.value
  dragDept.value = null
  if (from === null || from === target) return
  const depts = store.grouped.map((d) => d.dept)
  const moved = depts.splice(from, 1)[0]
  depts.splice(target, 0, moved)
  persist({ departments: depts, members: currentMembersOrder() })
}

/* ---- 个人级拖拽：仅组内重排 order.members[dept] ---- */
const dragMember = ref<{ dept: string; idx: number } | null>(null)
function onMemberDragStart(dept: string, idx: number) { dragMember.value = { dept, idx } }
function onMemberDrop(dept: string, target: number) {
  const d = dragMember.value
  dragMember.value = null
  if (!d || d.dept !== dept || d.idx === target) return  // 不允许跨部门
  const group = store.grouped.find((g) => g.dept === dept)!
  const names = group.members.map((m) => m.name)
  const moved = names.splice(d.idx, 1)[0]
  names.splice(target, 0, moved)
  const members = currentMembersOrder()
  members[dept] = names
  persist({ departments: store.grouped.map((g) => g.dept), members })
}

/* 当前各部门的个人顺序快照 */
function currentMembersOrder(): Record<string, string[]> {
  const m: Record<string, string[]> = {}
  for (const d of store.grouped) m[d.dept] = d.members.map((x) => x.name)
  return m
}

async function persist(order: MeetingReportOrder) {
  await store.saveOrder(order)
}
</script>

<style scoped>
.mr-tree { display: flex; flex-direction: column; height: 100%; }
/* 搜索区：贴近上框线 */
.mr-search { padding: 6px 8px 8px; display: flex; flex-direction: column; gap: 6px; }
/* 提示文字加大一号 */
.mr-search-input :deep(.el-input__inner) { font-size: 15px; }
.mr-search-input :deep(.el-input__inner::placeholder) { font-size: 15px; }
.mr-filter { display: flex; align-items: center; flex-wrap: wrap; gap: 2px 6px; }
.mr-filter-label { font-size: 12px; color: var(--c-ink-2); font-weight: 600; }
.mr-filter-group :deep(.el-checkbox) { margin-right: 8px; }
.mr-filter-group :deep(.el-checkbox__label) { font-size: 12px; padding-left: 4px; }
.mr-hint { font-size: 11px; color: var(--c-ink-3); }
.mr-scroll { flex: 1; overflow-y: auto; padding: 0 8px 8px; }
.mr-empty { padding: 20px; text-align: center; color: var(--c-ink-3); font-size: 13px; }
.mr-dept { margin-bottom: 6px; }
.mr-dept-head { display: flex; align-items: center; gap: 6px; padding: 4px 6px;
  border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 20px; }
.mr-dept-head:hover { filter: brightness(0.96); }
.swatch { width: 10px; height: 10px; border-radius: 2px; }
.mr-member { margin: 4px 0 4px 14px; }
.mr-member-head { display: flex; align-items: center; gap: 4px; padding: 2px 6px; border-radius: 5px;
  cursor: pointer; color: var(--c-ink-2); font-size: 18px; font-weight: 700; }
.mr-member-head:hover { background: var(--c-surface-2, #f2f3f5); }
/* 展开/折叠指示三角：展开 ▾ / 折叠 ▸，淡色小字 */
.caret { flex: none; width: 12px; text-align: center; font-size: 11px; color: var(--c-ink-3); user-select: none; }
.mr-proj { margin-left: 18px; padding: 3px 8px; border-radius: 5px; cursor: pointer;
  font-size: 15px; color: var(--c-ink-2); }
.mr-proj:hover { background: var(--c-surface-2, #f2f3f5); }
.mr-proj.cur { background: var(--c-accent, #3954d6); color: #fff; font-weight: 600; }
/* 项目名前的状态标签：用状态色；选中行反白时仍可读（继承白字） */
.mr-pst { font-weight: 700; margin-right: 2px; }
.mr-proj.cur .mr-pst { color: #fff !important; }
.grip { color: var(--c-ink-3); cursor: grab; }
</style>
