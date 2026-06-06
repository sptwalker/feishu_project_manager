import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { projectApi, departmentApi, settingsApi } from '@/api/resources'
import type { Project, Department, MeetingReportOrder } from '@/types'

/* 未分配兜底分组名（恒排在末尾） */
export const UNASSIGNED_DEPT = '未分配部门'
export const UNASSIGNED_OWNER = '未分配'

/* 仅汇报这三种状态：待启动/进行中/暂停 */
const REPORT_STATUSES = ['planned', 'in_progress', 'paused']

export interface MemberGroup { name: string; projects: Project[] }
export interface DeptGroup { dept: string; color?: string; members: MemberGroup[] }
/* 汇报序列里的一个"汇报位"=部门+个人 */
export interface PresenterSlot { dept: string; member: string }

export const useMeetingReportStore = defineStore('meetingReport', () => {
  const projects = ref<Project[]>([])
  const departments = ref<Department[]>([])
  const order = ref<MeetingReportOrder>({ departments: [], members: {} })
  const loading = ref(false)

  // 计时设置
  const totalMinutes = ref(120)              // 总时长提醒阈值（分钟）；超过即变色提醒，不强制结束
  const personThresholdMinutes = ref(5)

  // 当前选中
  const currentProjectId = ref<number | null>(null)

  // 计时运行时（均为正向计时，记录已经历时长，单位秒）
  const running = ref(false)
  const totalElapsed = ref(0)          // 会议已进行总时长
  const personElapsed = ref(0)         // 当前汇报人已用时长
  let timer: ReturnType<typeof setInterval> | null = null

  /* 部门容错映射：按全称或简称匹配部门记录（与总览页一致） */
  function findDepartment(name?: string | null): Department | undefined {
    if (!name) return undefined
    const key = name.trim()
    return departments.value.find((d) => d.name === key || d.short_name === key)
  }

  /* 通用：把 items 按 explicitOrder 排序，剩余按本地化名称，pinned 名称强制末尾 */
  function sortByOrder(items: string[], explicitOrder: string[], pinnedLast: string): string[] {
    const inOrder = explicitOrder.filter((x) => items.includes(x) && x !== pinnedLast)
    const rest = items
      .filter((x) => !inOrder.includes(x) && x !== pinnedLast)
      .sort((a, b) => a.localeCompare(b, 'zh'))
    const tail = items.includes(pinnedLast) ? [pinnedLast] : []
    return [...inOrder, ...rest, ...tail]
  }

  /* 把项目按 部门→个人 分组，套用已存顺序，未排到的按兜底排末尾 */
  const grouped = computed<DeptGroup[]>(() => {
    // 1. 收集 部门 -> 个人 -> 项目
    const deptMap = new Map<string, Map<string, Project[]>>()
    for (const p of projects.value) {
      if (!REPORT_STATUSES.includes(p.status)) continue
      const dept = (p.department && p.department.trim()) || UNASSIGNED_DEPT
      const owner = (p.owner_name && p.owner_name.trim()) || UNASSIGNED_OWNER
      if (!deptMap.has(dept)) deptMap.set(dept, new Map())
      const m = deptMap.get(dept)!
      if (!m.has(owner)) m.set(owner, [])
      m.get(owner)!.push(p)
    }
    // 2. 部门排序：先按 order.departments，未列出的按名称，未分配置末尾
    const allDepts = Array.from(deptMap.keys())
    const sortedDepts = sortByOrder(allDepts, order.value.departments, UNASSIGNED_DEPT)
    // 3. 组装
    return sortedDepts.map((dept) => {
      const memberMap = deptMap.get(dept)!
      const allMembers = Array.from(memberMap.keys())
      const memberOrder = order.value.members[dept] || []
      const sortedMembers = sortByOrder(allMembers, memberOrder, UNASSIGNED_OWNER)
      return {
        dept,
        color: findDepartment(dept)?.color || undefined,
        members: sortedMembers.map((name) => ({ name, projects: memberMap.get(name)! })),
      }
    })
  })

  /* 扁平汇报序列：用于上一位/下一位翻页 */
  const presenters = computed<PresenterSlot[]>(() =>
    grouped.value.flatMap((d) => d.members.map((m) => ({ dept: d.dept, member: m.name }))),
  )

  /* 当前选中项目对象 */
  const currentProject = computed<Project | null>(() =>
    projects.value.find((p) => p.id === currentProjectId.value) || null,
  )

  /* 当前汇报位索引（由当前项目反推所属 部门+个人） */
  const currentPresenterIndex = computed<number>(() => {
    const p = currentProject.value
    if (!p) return -1
    const dept = (p.department && p.department.trim()) || UNASSIGNED_DEPT
    const member = (p.owner_name && p.owner_name.trim()) || UNASSIGNED_OWNER
    return presenters.value.findIndex((s) => s.dept === dept && s.member === member)
  })

  /* 加载数据：项目 + 部门 + 顺序 + 计时设置 */
  async function load() {
    loading.value = true
    try {
      const [ps, ds, ord, timerCfg] = await Promise.all([
        projectApi.list({ limit: 500 }),  // 后端 limit 上限 500；会议仅汇报未完成项目，足够覆盖
        departmentApi.list(),
        settingsApi.getMeetingReportOrder(),
        settingsApi.getMeetingTimer(),
      ])
      projects.value = ps
      departments.value = ds
      order.value = ord
      totalMinutes.value = timerCfg.total_minutes
      personThresholdMinutes.value = timerCfg.person_threshold_minutes
      // 不在此重置计时（load 可能被「编辑后刷新」再次调用，避免清零正在走的计时）
      // 选中项目：保留当前选中（若仍存在），否则默认第一个汇报位的第一个项目
      const stillExists = projects.value.some((p) => p.id === currentProjectId.value)
      if (!stillExists) {
        const firstProj = grouped.value[0]?.members[0]?.projects[0]
        currentProjectId.value = firstProj?.id ?? null
      }
    } finally {
      loading.value = false
    }
  }

  /* 选中某项目 */
  function selectProject(id: number) {
    if (id === currentProjectId.value) return
    // 切换汇报人时重置单人计时（仅当所属汇报位变化）
    const prevIdx = currentPresenterIndex.value
    currentProjectId.value = id
    if (currentPresenterIndex.value !== prevIdx) personElapsed.value = 0
  }

  /* 上一位 / 下一位：跳到相邻汇报位的第一个项目 */
  function gotoPresenter(delta: number) {
    const idx = currentPresenterIndex.value
    const next = idx + delta
    if (next < 0 || next >= presenters.value.length) return
    const slot = presenters.value[next]
    const dept = grouped.value.find((d) => d.dept === slot.dept)
    const member = dept?.members.find((m) => m.name === slot.member)
    const proj = member?.projects[0]
    if (proj) {
      currentProjectId.value = proj.id
      personElapsed.value = 0
    }
  }
  const nextPresenter = () => gotoPresenter(1)
  const prevPresenter = () => gotoPresenter(-1)

  /* 计时：每秒 tick（正向累加） */
  function start() {
    if (running.value) return
    running.value = true
    timer = setInterval(() => {
      totalElapsed.value += 1
      personElapsed.value += 1
    }, 1000)
  }
  function stop() {
    running.value = false
    if (timer) { clearInterval(timer); timer = null }
  }
  function resetPerson() { personElapsed.value = 0 }

  /* 是否超时 */
  const personOvertime = computed(() => personElapsed.value >= personThresholdMinutes.value * 60)
  const totalOvertime = computed(() => totalElapsed.value >= totalMinutes.value * 60)

  /* 拖拽后保存顺序 */
  async function saveOrder(next: MeetingReportOrder) {
    order.value = next
    await settingsApi.setMeetingReportOrder(next)
  }

  return {
    projects, departments, order, loading,
    totalMinutes, personThresholdMinutes,
    currentProjectId, currentProject, currentPresenterIndex,
    running, totalElapsed, personElapsed,
    grouped, presenters, personOvertime, totalOvertime,
    load, selectProject, nextPresenter, prevPresenter,
    start, stop, resetPerson, saveOrder, findDepartment,
  }
})
