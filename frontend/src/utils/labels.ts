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
  low: '低', medium: '中', high: '高', urgent: '紧急',
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
  high: 'var(--c-status-blocked)',
  urgent: 'var(--c-status-overdue)',
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
