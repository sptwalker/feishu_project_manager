import type {
  ProjectStatus, ProjectUrgency, TaskStatus, TaskPriority,
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

export function isOverdue(dueDate?: string | null, status?: string): boolean {
  if (!dueDate) return false
  if (status === 'completed' || status === 'cancelled') return false
  return new Date(dueDate) < new Date(new Date().toDateString())
}
