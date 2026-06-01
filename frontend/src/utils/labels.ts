import type {
  ProjectStatus, ProjectUrgency, TaskStatus, TaskPriority, RiskStatus,
} from '@/types'

export const projectStatusLabel: Record<ProjectStatus, string> = {
  planned: '待启动',
  in_progress: '进行中',
  paused: '暂停',
  completed: '已完成',
  cancelled: '已取消',
}

export const projectStatusColor: Record<ProjectStatus, string> = {
  planned: 'var(--c-status-planned)',
  in_progress: 'var(--c-status-progress)',
  paused: 'var(--c-status-blocked)',
  completed: 'var(--c-status-done)',
  cancelled: 'var(--c-ink-3)',
}

export const urgencyLabel: Record<ProjectUrgency, string> = {
  low: '低', medium: '中', high: '高', urgent: '重要',
}

// 项目状态排序顺序（用于默认/下拉）
export const PROJECT_STATUS_ORDER: ProjectStatus[] = [
  'planned', 'in_progress', 'paused', 'completed', 'cancelled',
]

// 紧急程度权重（数值越大越紧急，用于排序：紧急 > 高 > 中 > 低）
export const urgencyWeight: Record<ProjectUrgency, number> = {
  urgent: 4, high: 3, medium: 2, low: 1,
}

export const urgencyColor: Record<ProjectUrgency, string> = {
  low: 'var(--c-ink-3)',
  medium: 'var(--c-status-progress)',
  high: '#EF8A8A',     // 高优先级：浅红
  urgent: '#C0392B',   // 重要：深红
}

export const taskStatusLabel: Record<TaskStatus, string> = {
  pending: '待办',
  in_progress: '进行中',
  completed: '已完成',
  blocked: '阻塞',
}

export const taskStatusColor: Record<TaskStatus, string> = {
  pending: 'var(--c-status-planned)',
  in_progress: 'var(--c-status-progress)',
  completed: 'var(--c-status-done)',
  blocked: 'var(--c-status-blocked)',
}

export const taskStatusSoft: Record<TaskStatus, string> = {
  pending: 'var(--c-canvas)',
  in_progress: 'var(--c-status-progress-soft)',
  completed: 'var(--c-status-done-soft)',
  blocked: 'var(--c-status-blocked-soft)',
}

export const priorityLabel: Record<TaskPriority, string> = {
  low: '低', medium: '中', high: '高',
}

export const TASK_STATUS_ORDER: TaskStatus[] = ['pending', 'in_progress', 'completed', 'blocked']

export const riskStatusLabel: Record<RiskStatus, string> = {
  open: '未关闭',
  monitoring: '监控中',
  resolved: '已解决',
}

export const riskStatusColor: Record<RiskStatus, string> = {
  open: 'var(--c-status-overdue)',
  monitoring: 'var(--c-status-blocked)',
  resolved: 'var(--c-status-done)',
}

export const riskStatusSoft: Record<RiskStatus, string> = {
  open: 'var(--c-status-overdue-soft)',
  monitoring: 'var(--c-status-blocked-soft)',
  resolved: 'var(--c-status-done-soft)',
}

export const RISK_STATUS_ORDER: RiskStatus[] = ['open', 'monitoring', 'resolved']

export const roleLabel: Record<string, string> = {
  admin: '管理员',
  project_manager: '项目经理',
  member: '成员',
  observer: '观察者',
}

export const ROLE_OPTIONS = [
  { value: 'admin', label: '管理员' },
  { value: 'project_manager', label: '项目经理' },
  { value: 'member', label: '成员' },
  { value: 'observer', label: '观察者' },
]

export function isOverdue(dueDate?: string | null, status?: string): boolean {
  if (!dueDate) return false
  if (status === 'completed' || status === 'cancelled') return false
  return new Date(dueDate) < new Date(new Date().toDateString())
}

// 项目进展记录的「状况」选项与对应时间节点颜色
export const PROGRESS_STATUSES = [
  '正常', '延迟', '暂停', '阻塞', '等待', '待讨论', '待执行', '待确认',
] as const

// 未结束事件状态（时间线空心闪烁圆点 + 可反馈）
export const PENDING_STATUSES = ['待讨论', '待确认', '待执行'] as const

export const progressStatusColor: Record<string, string> = {
  正常: '#3DBE7B',   // 绿
  延迟: '#E6B422',   // 黄
  暂停: '#9AA0A6',   // 灰
  阻塞: '#E5484D',   // 红
  等待: '#7FB3E8',   // 淡蓝
  待讨论: '#E8833A', // 橙
  待执行: '#21C7C7', // 青
  待确认: '#E87FB0', // 粉
}

/* 完成度进度条渐变：随完成度从浅到深的同色系绿。
   completion 0→100 映射为浅→深，返回 CSS linear-gradient（左浅右深）。 */
export function completionGradient(completion: number): string {
  const c = Math.max(0, Math.min(100, completion))
  // 浅绿 #A7E8C4 → 深绿 #1E8E54，按完成度插值起止色
  const light = mixHex('#C5EFD9', '#3DBE7B', c / 100)
  const dark = mixHex('#3DBE7B', '#1E8E54', c / 100)
  return `linear-gradient(90deg, ${light} 0%, ${dark} 100%)`
}

/* 十六进制颜色按比例 t(0..1) 线性混合 */
function mixHex(from: string, to: string, t: number): string {
  const a = hexToRgb(from)
  const b = hexToRgb(to)
  const r = Math.round(a[0] + (b[0] - a[0]) * t)
  const g = Math.round(a[1] + (b[1] - a[1]) * t)
  const bl = Math.round(a[2] + (b[2] - a[2]) * t)
  return `rgb(${r}, ${g}, ${bl})`
}

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '')
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ]
}
