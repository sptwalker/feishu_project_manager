// 与后端 schema 对应的类型定义

export type ProjectStatus = 'planned' | 'in_progress' | 'paused' | 'completed' | 'cancelled'
export type ProjectUrgency = 'low' | 'medium' | 'high' | 'urgent'
export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'blocked'
export type TaskPriority = 'low' | 'medium' | 'high'
export type RiskStatus = 'open' | 'monitoring' | 'resolved'

export interface User {
  id: number
  feishu_user_id: string
  name: string
  name_en?: string | null
  position?: string | null
  avatar_url?: string | null
  department?: string | null
  role: string
  last_login_at?: string | null
  created_at?: string
  updated_at?: string
}

export interface Department {
  id: number
  name: string
  short_name?: string | null
  leader?: string | null
  responsibility?: string | null
  color?: string | null
  created_at?: string
  updated_at?: string
}

export interface DocumentAttachment {
  url: string
  title?: string | null
  added_at: string
}

export interface AnnotationReply {
  id: string
  author_name: string
  content: string
  created_at: string
}

export interface Annotation {
  id: string
  author_name: string
  content: string
  created_at: string
  replies?: AnnotationReply[] | null
}

export interface ProgressEntry {
  time: string
  content: string
  status: string
  meeting_session?: number | null
  id?: string | null
  reply_to?: string | null
  annotations?: Annotation[] | null
  attachments?: DocumentAttachment[] | null
  // 仅前端编辑态使用的临时标记：标识本次编辑会话中新增（点"添加一条"）的行，用于显示"周会记录："标签。不持久化到后端。
  _isNew?: boolean
}

export interface MeetingState {
  active: boolean
  base_monday: string
  base_count: number
  this_week_monday: string
  this_week_count: number
  this_week_recorded: boolean
  last_meeting: { date: string; count: number } | null
  calibration_count: number
  calibration_monday: string
  // 事件驱动周期（上次会议日期 + new_cycle_days 天进入新周期）
  can_open_new_cycle?: boolean
  next_count?: number
  days_since_last?: number | null
  new_cycle_days?: number
}

export interface MeetingItem {
  dept?: string | null
  dept_short?: string | null
  dept_color?: string | null
  project: string
  owner?: string | null
  status: string
  content: string
  time: string
  urgency: string
}

export interface MeetingRecordDetail {
  session: number
  meeting_date?: string | null
  recorder?: string | null
  status: string
  doc_url?: string | null
  items: MeetingItem[]
}

export interface MeetingSessions {
  sessions: number[]
  current: number
}

export interface MeetingSendResult {
  ok: boolean
  doc_url?: string | null
  message: string
}

export interface Project {
  id: number
  name: string
  record_date: string
  content?: string | null
  status: ProjectStatus
  urgency: ProjectUrgency
  department?: string | null
  owner_name?: string | null
  related_name?: string | null
  completion: number
  is_long_term?: boolean
  estimated_end_date?: string | null
  actual_end_date?: string | null
  progress_log?: ProgressEntry[] | null
  created_at: string
  updated_at: string
}

export interface Task {
  id: number
  project_id: number
  parent_task_id?: number | null
  name: string
  description?: string | null
  owner_name?: string | null
  status: TaskStatus
  priority: TaskPriority
  completion: number
  due_date?: string | null
  start_date?: string | null
  end_date?: string | null
  created_at: string
  updated_at: string
}

export interface Risk {
  id: number
  project_id: number
  title: string
  description?: string | null
  status: RiskStatus
  owner_name?: string | null
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
