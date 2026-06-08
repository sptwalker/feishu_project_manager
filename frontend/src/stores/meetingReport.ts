import { defineStore, acceptHMRUpdate } from 'pinia'
import { ref, computed, watch } from 'vue'
import { projectApi, departmentApi, settingsApi, timerApi } from '@/api/resources'
import type { Project, Department, MeetingReportOrder, TimerState } from '@/types'

/* 未分配兜底分组名（恒排在末尾） */
export const UNASSIGNED_DEPT = '未分配部门'
export const UNASSIGNED_OWNER = '未分配'

/* 默认隐藏的项目状态：暂停/已完成/已取消（左侧多选可切换）；进行中/待启动默认显示 */
const DEFAULT_HIDDEN_STATUSES = ['paused', 'completed', 'cancelled']

/* 本端浏览器唯一 id（localStorage 持久化）：主控刷新后用同一 id 重连续权 */
const CLIENT_ID_KEY = 'fpm_meeting_client_id'
function getClientId(): string {
  let id = localStorage.getItem(CLIENT_ID_KEY)
  if (!id) {
    id = `c-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
    localStorage.setItem(CLIENT_ID_KEY, id)
  }
  return id
}

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

  // 浏览焦点：本端自由切换/编辑的项目（与计时焦点解耦，协助端浏览不影响计时）
  const currentProjectId = ref<number | null>(null)

  // ---- 服务端计时（锚点 + 本地推算）----
  const clientId = getClientId()
  const role = ref<'controller' | 'assistant' | 'none'>('none')
  const timer = ref<TimerState | null>(null)   // 服务端最近一次返回的计时状态
  let clockOffsetMs = 0                          // server_now - client_now，用于时钟漂移校正
  const tickNow = ref(Date.now())               // 每秒推进，驱动推算 computed 重算
  let tickHandle: ReturnType<typeof setInterval> | null = null
  let pollHandle: ReturnType<typeof setInterval> | null = null
  let heartbeatHandle: ReturnType<typeof setInterval> | null = null

  /* 角色 / 计时运行态 / 主控在线 */
  const isController = computed(() => role.value === 'controller')
  const running = computed(() => timer.value?.status === 'running')
  const controllerPresent = computed(() => !!timer.value?.controller_present)
  const controllerOnline = computed(() => !!timer.value?.controller_online)
  const pausedReason = computed(() => timer.value?.paused_reason ?? null)
  /* 主控已释放（掉线超阈值，无主控）：协助端可接管 */
  const controllerReleased = computed(() => !!timer.value?.active && !controllerPresent.value)
  /* 主控掉线但未释放（计时已自动暂停，等待重连） */
  const controllerOffline = computed(() =>
    !!timer.value?.active && controllerPresent.value && !controllerOnline.value)

  /* 校正后的当前毫秒（用 tickNow 触发响应式 + 时钟偏移） */
  function serverNowMs(): number { return tickNow.value + clockOffsetMs }
  function parseMs(s?: string | null): number | null {
    if (!s) return null
    const t = new Date(s).getTime()
    return Number.isNaN(t) ? null : t
  }

  /* 会议总时长（秒）：本地推算 = total_base + (运行中 ? now - total_started_at : 0) */
  const totalElapsed = computed<number>(() => {
    const t = timer.value
    if (!t || !t.active) return 0
    let s = t.total_base ?? 0
    if (t.status === 'running') {
      const st = parseMs(t.total_started_at)
      if (st) s += Math.max(0, Math.floor((serverNowMs() - st) / 1000))
    }
    return s
  })

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

  /* 当前【浏览】项目反推的汇报位键（部门|个人）——用于左树高亮、项目翻页等浏览逻辑 */
  const browsePresenterKey = computed<string>(() => {
    const p = currentProject.value
    if (!p) return ''
    const dept = (p.department && p.department.trim()) || UNASSIGNED_DEPT
    const member = (p.owner_name && p.owner_name.trim()) || UNASSIGNED_OWNER
    return `${dept}|${member}`
  })
  /* 当前【计时】汇报人键：来自服务端（主控选定），与浏览解耦 */
  const timingPresenterKey = computed<string>(() => timer.value?.current_presenter_key || '')

  /* 各汇报人累计用时（秒）= person_base + (该人正在计时段 ? now - segment_started_at : 0) */
  const personTimes = computed<Record<string, number>>(() => {
    const t = timer.value
    const base: Record<string, number> = { ...(t?.person_base || {}) }
    if (t?.active && t.status === 'running' && t.current_presenter_key) {
      const seg = parseMs(t.segment_started_at)
      if (seg) {
        const extra = Math.max(0, Math.floor((serverNowMs() - seg) / 1000))
        base[t.current_presenter_key] = (base[t.current_presenter_key] || 0) + extra
      }
    }
    return base
  })
  /* 当前【计时】汇报人已用时长（秒）——顶栏主席台显示用 */
  const personElapsed = computed<number>(() => personTimes.value[timingPresenterKey.value] || 0)

  /* 各汇报人用时统计（取个人名、降序、过滤0秒）：供顶栏统计弹窗与结束柱状图复用 */
  const personTimeStats = computed<{ name: string; seconds: number }[]>(() =>
    Object.entries(personTimes.value)
      .map(([key, seconds]) => ({ name: key.split('|')[1] || key, seconds }))
      .filter((x) => x.seconds > 0)
      .sort((a, b) => b.seconds - a.seconds),
  )

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

  /* 选中某项目（浏览焦点，本端本地切换，任何端都可自由浏览，不影响计时）。
     主控选中时若该项目属于不同汇报人，则同步推进服务端计时焦点。 */
  function selectProject(id: number) {
    currentProjectId.value = id
    syncTimingPresenterIfController()
  }

  /* 主控：若浏览到的汇报人与当前计时汇报人不同，推进服务端计时焦点（切人结算）。
     协助端不发送，浏览不改计时。 */
  function syncTimingPresenterIfController() {
    if (role.value !== 'controller' || !timer.value?.active) return
    const key = browsePresenterKey.value
    if (key && key !== timingPresenterKey.value) {
      timerApi.control(clientId, 'select_presenter', key).then(applyTimerState).catch(() => {})
    }
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

  // ---- 服务端计时：状态应用 + 生命周期 ----

  /* 用服务端返回的计时状态刷新本地：更新 role、时钟偏移、timer 锚点 */
  function applyTimerState(st: TimerState) {
    timer.value = st
    role.value = st.my_role
    const sv = parseMs(st.server_now)
    if (sv) clockOffsetMs = sv - Date.now()
  }

  /* 进入汇报页：拉一次状态 → 管理员认领主控 → 启动 tick/轮询/心跳。
     非管理员（认领失败/无权）保持协助态，只轮询不心跳。 */
  async function connectTimer(isAdmin: boolean) {
    try {
      if (isAdmin) {
        // 认领主控（不自动开始计时：进入后由主控手动点 ▶ 开始）
        applyTimerState(await timerApi.claim(clientId))
      } else {
        applyTimerState(await timerApi.state(clientId))
      }
    } catch { /* 无进行中周会等：保持 none，UI 兜底 */ }

    // 本地每秒 tick：仅驱动推算 computed 重算，不写任何状态
    if (!tickHandle) tickHandle = setInterval(() => { tickNow.value = Date.now() }, 1000)
    // 轮询服务端状态（4s）：同步他端的切人/暂停/掉线判定
    if (!pollHandle) pollHandle = setInterval(refreshTimer, 4000)
    // 主控心跳（5s）：维持存活 + 掉线后重连自动续
    if (!heartbeatHandle) heartbeatHandle = setInterval(sendHeartbeat, 5000)
  }

  async function refreshTimer() {
    try { applyTimerState(await timerApi.state(clientId)) } catch { /* 忽略瞬时失败 */ }
  }

  async function sendHeartbeat() {
    if (role.value !== 'controller') return
    try { applyTimerState(await timerApi.heartbeat(clientId)) } catch { /* 忽略 */ }
  }

  /* 离开汇报页：停掉所有定时器（不影响服务端，掉线由服务端惰性判定） */
  function disconnectTimer() {
    if (tickHandle) { clearInterval(tickHandle); tickHandle = null }
    if (pollHandle) { clearInterval(pollHandle); pollHandle = null }
    if (heartbeatHandle) { clearInterval(heartbeatHandle); heartbeatHandle = null }
  }

  /* 主控：开始/继续计时 */
  async function startTiming() {
    if (role.value !== 'controller') return
    try {
      applyTimerState(await timerApi.control(clientId, 'resume'))
      syncTimingPresenterIfController()  // 开始后把计时焦点对齐到当前浏览的汇报人
    } catch { /* 忽略 */ }
  }
  /* 主控：暂停计时 */
  async function pauseTiming() {
    if (role.value !== 'controller') return
    try { applyTimerState(await timerApi.control(clientId, 'pause')) } catch { /* 忽略 */ }
  }
  /* 协助端：接管主控（主控已释放时） */
  async function takeoverControl() {
    try {
      applyTimerState(await timerApi.takeover(clientId, timer.value?.controller_version ?? null))
    } catch { /* 冲突/仍在线由 UI 提示后刷新 */ await refreshTimer() }
  }

  /* 结束会议本地清理：停定时器、清浏览焦点与过滤（服务端计时由 close 接口清空） */
  function reset() {
    disconnectTimer()
    timer.value = null
    role.value = 'none'
    currentProjectId.value = null
    hiddenStatuses.value = [...DEFAULT_HIDDEN_STATUSES]
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
    running, totalElapsed, personElapsed, personTimes, personTimeStats,
    grouped, presenters, personOvertime, totalOvertime,
    // 计时 + 主控
    clientId, role, isController, timer,
    controllerPresent, controllerOnline, controllerReleased, controllerOffline, pausedReason,
    timingPresenterKey,
    connectTimer, disconnectTimer, startTiming, pauseTiming, takeoverControl,
    load, selectProject, nextPresenter, prevPresenter, prevPresenterTail,
    nextProjectInMember, prevProjectInMember,
    reset, saveOrder, findDepartment,
  }
})

// Pinia HMR 加固：开发模式下修改本 store 文件时正确热替换已实例化的 store，
// 否则旧逻辑会残留到整页刷新（表现为「改了代码但页面行为没更新」）。
if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useMeetingReportStore, import.meta.hot))
}
