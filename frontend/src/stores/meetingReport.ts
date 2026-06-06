import { defineStore, acceptHMRUpdate } from 'pinia'
import { ref, computed, watch } from 'vue'
import { projectApi, departmentApi, settingsApi } from '@/api/resources'
import type { Project, Department, MeetingReportOrder } from '@/types'

/* 未分配兜底分组名（恒排在末尾） */
export const UNASSIGNED_DEPT = '未分配部门'
export const UNASSIGNED_OWNER = '未分配'

/* 默认隐藏的项目状态：暂停/已完成/已取消（左侧多选可切换）；进行中/待启动默认显示 */
const DEFAULT_HIDDEN_STATUSES = ['paused', 'completed', 'cancelled']

export interface MemberGroup { name: string; projects: Project[] }
export interface DeptGroup { dept: string; color?: string; members: MemberGroup[] }
/* 汇报序列里的一个"汇报位"=部门+个人 */
export interface PresenterSlot { dept: string; member: string }

export const useMeetingReportStore = defineStore('meetingReport', () => {
  const projects = ref<Project[]>([])
  const departments = ref<Department[]>([])
  const order = ref<MeetingReportOrder>({ departments: [], members: {} })
  const loading = ref(false)
  // 左侧多选「不显示」：被勾选的状态从列表与翻页中排除（默认隐藏 暂停/已完成/已取消）
  const hiddenStatuses = ref<string[]>([...DEFAULT_HIDDEN_STATUSES])

  // 计时设置
  const totalMinutes = ref(120)              // 总时长提醒阈值（分钟）；超过即变色提醒，不强制结束
  const personThresholdMinutes = ref(5)

  // 当前选中
  const currentProjectId = ref<number | null>(null)

  // 计时运行时（均为正向计时，记录已经历时长，单位秒）
  const running = ref(false)
  const totalElapsed = ref(0)          // 会议已进行总时长
  // 每个汇报位（部门|个人）的累计用时（秒）；会议期间持续累计，切换汇报人不清零
  const personTimes = ref<Record<string, number>>({})
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
      if (hiddenStatuses.value.includes(p.status)) continue
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

  /* 当前汇报位的唯一键（部门|个人），用于按汇报人累计用时 */
  const currentPresenterKey = computed<string>(() => {
    const p = currentProject.value
    if (!p) return ''
    const dept = (p.department && p.department.trim()) || UNASSIGNED_DEPT
    const member = (p.owner_name && p.owner_name.trim()) || UNASSIGNED_OWNER
    return `${dept}|${member}`
  })
  /* 当前汇报人已用时长（秒）= 其在会议期间的累计值 */
  const personElapsed = computed<number>(() => personTimes.value[currentPresenterKey.value] || 0)

  /* 当前汇报人（部门+个人）名下的项目列表（已按隐藏状态过滤、按顺序） */
  const currentMemberProjects = computed<Project[]>(() => {
    const idx = currentPresenterIndex.value
    if (idx < 0) return []
    const slot = presenters.value[idx]
    const dept = grouped.value.find((d) => d.dept === slot.dept)
    return dept?.members.find((m) => m.name === slot.member)?.projects ?? []
  })
  /* 当前项目在「当前汇报人项目列表」中的下标 */
  const currentProjectIndexInMember = computed<number>(() =>
    currentMemberProjects.value.findIndex((p) => p.id === currentProjectId.value),
  )
  /* 在当前汇报人范围内切换上一个/下一个项目（不重置单人计时；越界忽略） */
  function gotoProjectInMember(delta: number) {
    const list = currentMemberProjects.value
    const i = currentProjectIndexInMember.value
    const next = i + delta
    if (i < 0 || next < 0 || next >= list.length) return
    currentProjectId.value = list[next].id
  }
  const nextProjectInMember = () => gotoProjectInMember(1)
  const prevProjectInMember = () => gotoProjectInMember(-1)

  /* 当前选中项被隐藏/移出可见列表时，自动切到第一个可见项目（避免右侧挂着已隐藏项目） */
  watch(grouped, (groups) => {
    if (currentProjectId.value === null) return
    const visible = new Set(groups.flatMap((d) => d.members.flatMap((m) => m.projects.map((p) => p.id))))
    if (!visible.has(currentProjectId.value)) {
      currentProjectId.value = groups[0]?.members[0]?.projects[0]?.id ?? null
    }
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

  /* 选中某项目（切换汇报人不清零计时，各汇报人用时各自累计） */
  function selectProject(id: number) {
    currentProjectId.value = id
  }

  /* 上一位 / 下一位：跳到相邻汇报位的项目
     landOnLast=true 时落到目标汇报位的「最后一个」项目（向前翻页用，保持连续手感），否则落到第一个 */
  function gotoPresenter(delta: number, landOnLast = false) {
    const idx = currentPresenterIndex.value
    const next = idx + delta
    if (next < 0 || next >= presenters.value.length) return
    const slot = presenters.value[next]
    const dept = grouped.value.find((d) => d.dept === slot.dept)
    const member = dept?.members.find((m) => m.name === slot.member)
    const list = member?.projects ?? []
    const proj = landOnLast ? list[list.length - 1] : list[0]
    if (proj) {
      currentProjectId.value = proj.id
    }
  }
  const nextPresenter = () => gotoPresenter(1)
  const prevPresenter = () => gotoPresenter(-1)
  /* 向前翻页专用：跳到上一位汇报人的「最后一个」项目，让项目级翻页跨汇报人也连续 */
  const prevPresenterTail = () => gotoPresenter(-1, true)

  /* 计时：每秒 tick（正向累加） */
  function start() {
    if (running.value) return
    running.value = true
    timer = setInterval(() => {
      totalElapsed.value += 1
      // 给当前汇报人累加用时（切换汇报人后各自累计、互不清零）
      const key = currentPresenterKey.value
      if (key) personTimes.value[key] = (personTimes.value[key] || 0) + 1
    }, 1000)
  }
  function stop() {
    running.value = false
    if (timer) { clearInterval(timer); timer = null }
  }

  /* 结束会议：停止计时并清空所有周会运行时状态，下次进入汇报页从零开始 */
  function reset() {
    stop()                                              // 停止计时器
    totalElapsed.value = 0                              // 会议总计时归零
    personTimes.value = {}                              // 每位汇报人累计用时清空
    currentProjectId.value = null                       // 取消选中项目
    hiddenStatuses.value = [...DEFAULT_HIDDEN_STATUSES] // 过滤状态恢复默认
  }

  /* 是否超时 */
  const personOvertime = computed(() => personElapsed.value >= personThresholdMinutes.value * 60)
  const totalOvertime = computed(() => totalElapsed.value >= totalMinutes.value * 60)

  /* 拖拽后保存顺序 */
  async function saveOrder(next: MeetingReportOrder) {
    order.value = next
    await settingsApi.setMeetingReportOrder(next)
  }

  return {
    projects, departments, order, loading, hiddenStatuses,
    totalMinutes, personThresholdMinutes,
    currentProjectId, currentProject, currentPresenterIndex,
    currentMemberProjects, currentProjectIndexInMember,
    running, totalElapsed, personElapsed,
    grouped, presenters, personOvertime, totalOvertime,
    load, selectProject, nextPresenter, prevPresenter, prevPresenterTail,
    nextProjectInMember, prevProjectInMember,
    start, stop, reset, saveOrder, findDepartment,
  }
})

// Pinia HMR 加固：开发模式下修改本 store 文件时正确热替换已实例化的 store，
// 否则旧逻辑会残留到整页刷新（表现为「改了代码但页面行为没更新」）。
if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useMeetingReportStore, import.meta.hot))
}
