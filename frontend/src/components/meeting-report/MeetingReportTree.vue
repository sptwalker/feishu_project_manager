<template>
  <div class="mr-tree">
    <div class="mr-search">
      <el-input v-model="keyword" placeholder="🔍 查找项目 / 负责人 / 部门" clearable size="small" />
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
        <div class="mr-dept-head">
          <span class="grip">⇅</span>
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
          <div class="mr-member-head">
            <span class="grip">⇅</span>{{ m.name }} ({{ m.projects.length }})
          </div>
          <div
            v-for="p in m.projects"
            :key="p.id"
            class="mr-proj"
            :class="{ cur: p.id === store.currentProjectId }"
            @click="store.selectProject(p.id)"
          >
            • {{ p.name }}
          </div>
        </div>
      </div>
      <div v-if="!filteredGroups.length" class="mr-empty">无匹配项目</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElInput } from 'element-plus'
import { useMeetingReportStore } from '@/stores/meetingReport'
import type { MeetingReportOrder } from '@/types'

const store = useMeetingReportStore()
const keyword = ref('')

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
.mr-search { padding: 8px; display: flex; flex-direction: column; gap: 4px; }
.mr-hint { font-size: 11px; color: var(--c-ink-3); }
.mr-scroll { flex: 1; overflow-y: auto; padding: 0 8px 8px; }
.mr-empty { padding: 20px; text-align: center; color: var(--c-ink-3); font-size: 13px; }
.mr-dept { margin-bottom: 6px; }
.mr-dept-head { display: flex; align-items: center; gap: 6px; padding: 4px 6px;
  background: var(--c-surface-2, #f2f3f5); border-radius: 6px; font-weight: 600; cursor: grab; }
.swatch { width: 10px; height: 10px; border-radius: 2px; }
.mr-member { margin: 4px 0 4px 14px; }
.mr-member-head { display: flex; align-items: center; gap: 4px; padding: 2px 6px;
  cursor: grab; color: var(--c-ink-2); }
.mr-proj { margin-left: 18px; padding: 3px 8px; border-radius: 5px; cursor: pointer;
  font-size: 13px; color: var(--c-ink-2); }
.mr-proj:hover { background: var(--c-surface-2, #f2f3f5); }
.mr-proj.cur { background: var(--c-accent, #3954d6); color: #fff; font-weight: 600; }
.grip { color: var(--c-ink-3); cursor: grab; }
</style>
