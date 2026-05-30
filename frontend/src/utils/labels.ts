import type {
  ProjectStatus, ProjectUrgency, TaskStatus, TaskPriority, RiskStatus,
} from '@/types'

export const projectStatusLabel: Record<ProjectStatus, string> = {
  planned: '待启动',
  in_progress: '进行中',
  completed: '已完成',
  cancelled: '已取消',
}

export const projectStatusColor: Record<ProjectStatus, string> = {
  planned: 'var(--c-status-planned)',
  in_progress: 'var(--c-status-progress)',
  completed: 'var(--c-status-done)',
  cancelled: 'var(--c-ink-3)',
}

export const urgencyLabel: Record<ProjectUrgency, string> = {
  low: '低', medium: '中', high: '高', urgent: '紧急',
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
