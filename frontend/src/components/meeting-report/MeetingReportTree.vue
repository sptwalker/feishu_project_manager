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
            <template v-for="node in memberTree(m.projects)" :key="node.id">
              <!-- 顶层项目 / 项目组容器 -->
              <div
                class="mr-proj"
                :class="{ cur: node.id === store.currentProjectId, 'is-group': node.is_group }"
                @click="store.selectProject(node.id)"
              >
                <span v-if="node._kids.length" class="mr-gtoggle" @click.stop="toggleGroup(node.id)">{{ isGroupOpen(node.id) ? '▾' : '▸' }}</span>
                <span v-if="node.is_group" class="mr-gtag">组</span>
                <span class="mr-pst" :style="{ color: statusColor(node.status) }">【{{ statusLabel(node.status) }}】</span>{{ node.name }}
              </div>
              <!-- 项目组子项：缩进 + 分支线（末项为肘弯 └，其余贯穿 ├） -->
              <template v-if="node._kids.length && isGroupOpen(node.id)">
                <div
                  v-for="(kid, ki) in node._kids"
                  :key="kid.id"
                  class="mr-proj mr-proj-kid"
                  :class="{ cur: kid.id === store.currentProjectId }"
                  @click="store.selectProject(kid.id)"
                >
                  <span class="mr-branch" :class="{ last: ki === node._kids.length - 1 }"></span>
                  <span class="mr-pst" :style="{ color: statusColor(kid.status) }">【{{ statusLabel(kid.status) }}】</span>{{ kid.name }}
                </div>
              </template>
            </template>
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
import type { MeetingReportOrder, ProjectStatus, Project } from '@/types'

const store = useMeetingReportStore()
const keyword = ref('')

/* 项目状态中文标签 / 颜色 */
const statusLabel = (s: ProjectStatus) => projectStatusLabel[s]
const statusColor = (s: ProjectStatus) => projectStatusColor[s]

/* 把某汇报人名下的扁平项目列表整理成「项目组→子项」树：
   子项（parent_id 命中同列表内的组）挂到组下；其余（含组容器、独立项目）留在顶层。 */
type TreeNode = Project & { _kids: Project[] }
function memberTree(list: Project[]): TreeNode[] {
  const ids = new Set(list.map((p) => p.id))
  const kidsOf = new Map<number, Project[]>()
  const top: Project[] = []
  for (const p of list) {
    if (p.parent_id != null && ids.has(p.parent_id)) {
      const arr = kidsOf.get(p.parent_id) ?? []
      arr.push(p)
      kidsOf.set(p.parent_id, arr)
    } else {
      top.push(p)
    }
  }
  return top.map((p) => ({ ...p, _kids: p.is_group ? (kidsOf.get(p.id) ?? []) : [] }))
}

/* 项目组展开/折叠：默认展开；记录被折叠的组 id；搜索时强制全展开 */
const collapsedGroups = ref<Set<number>>(new Set())
function toggleGroup(id: number) {
  const s = new Set(collapsedGroups.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  collapsedGroups.value = s
}
function isGroupOpen(id: number): boolean {
  if (keyword.value.trim()) return true
  return !collapsedGroups.value.has(id)
}

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
/* 项目组容器行：折叠三角 + 「组」标签 */
.mr-proj.is-group { font-weight: 600; }
.mr-gtoggle { display: inline-block; width: 14px; text-align: center; margin-right: 2px;
  font-size: 11px; color: var(--c-ink-3); user-select: none; }
.mr-proj.cur .mr-gtoggle { color: #fff; }
.mr-gtag { display: inline-block; margin-right: 4px; padding: 0 5px; border-radius: 3px;
  background: var(--c-accent, #3954d6); color: #fff; font-size: 11px; font-weight: 700; vertical-align: 1px; }
.mr-proj.cur .mr-gtag { background: #fff; color: var(--c-accent, #3954d6); }
/* 子项：再缩进一层，带树状分支线（末项肘弯 └，其余贯穿 ├） */
.mr-proj-kid { margin-left: 34px; position: relative; padding-left: 16px; }
.mr-branch { position: absolute; left: 0; top: 0; bottom: 0; width: 12px; }
.mr-branch::before { content: ''; position: absolute; left: 4px; top: -3px; bottom: -3px;
  border-left: 1px solid var(--c-border-strong, #c0c4cc); }
.mr-branch::after { content: ''; position: absolute; left: 4px; top: 50%; width: 8px;
  border-top: 1px solid var(--c-border-strong, #c0c4cc); }
.mr-branch.last::before { bottom: 50%; }
/* 项目名前的状态标签：用状态色；选中行反白时仍可读（继承白字） */
.mr-pst { font-weight: 700; margin-right: 2px; }
.mr-proj.cur .mr-pst { color: #fff !important; }
.grip { color: var(--c-ink-3); cursor: grab; }
</style>
