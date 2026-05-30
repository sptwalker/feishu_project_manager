// 与后端 schema 对应的类型定义

export type ProjectStatus = 'planned' | 'in_progress' | 'completed' | 'cancelled'
export type ProjectUrgency = 'low' | 'medium' | 'high' | 'urgent'
export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'blocked'
export type TaskPriority = 'low' | 'medium' | 'high'
export type RiskStatus = 'open' | 'monitoring' | 'resolved'

export interface User {
  id: number
  feishu_user_id: string
  name: string
  avatar_url?: string | null
  department?: string | null
  role: string
}

export interface Project {
  id: number
  name: string
  record_date: string
  content?: string | null
  status: ProjectStatus
  urgency: ProjectUrgency
  department?: string | null
  owner_id: number
  completion: number
  estimated_end_date?: string | null
  actual_end_date?: string | null
  created_at: string
  updated_at: string
}

export interface Task {
  id: number
  project_id: number
  parent_task_id?: number | null
  name: string
  description?: string | null
  owner_id: number
  status: TaskStatus
  priority: TaskPriority
  completion: number
  due_date?: string | null
  start_date?: string | null
  end_date?: string | null
  created_at: string
  updated_at: string
}

export interface DashboardStats {
  projects: {
    total: number
    by_status: Record<string, number>
    avg_completion: number
    overdue: number
  }
  tasks: {
    total: number
    by_status: Record<string, number>
    overdue: number
  }
  risks: {
    total: number
    by_status: Record<string, number>
  }
}

export interface Token {
  access_token: string
  refresh_token: string
  token_type: string
}
