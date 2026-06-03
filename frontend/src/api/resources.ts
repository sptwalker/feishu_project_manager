import api from './client'
import type { Project, Task, Risk, User, Department, DashboardStats, MeetingState, MeetingRecordDetail, MeetingSessions, MeetingSendResult } from '@/types'

export const projectApi = {
  list(params?: Record<string, unknown>) {
    return api.get<Project[]>('/projects/', { params }).then((r) => r.data)
  },
  get(id: number) {
    return api.get<Project>(`/projects/${id}`).then((r) => r.data)
  },
  create(payload: Partial<Project>) {
    return api.post<Project>('/projects/', payload).then((r) => r.data)
  },
  update(id: number, payload: Partial<Project>) {
    return api.put<Project>(`/projects/${id}`, payload).then((r) => r.data)
  },
  remove(id: number) {
    return api.delete(`/projects/${id}`)
  },
}

export const taskApi = {
  listByProject(projectId: number, params?: Record<string, unknown>) {
    return api.get<Task[]>(`/projects/${projectId}/tasks`, { params }).then((r) => r.data)
  },
  get(id: number) {
    return api.get<Task>(`/tasks/${id}`).then((r) => r.data)
  },
  create(projectId: number, payload: Partial<Task>) {
    return api.post<Task>(`/projects/${projectId}/tasks`, payload).then((r) => r.data)
  },
  update(id: number, payload: Partial<Task>) {
    return api.put<Task>(`/tasks/${id}`, payload).then((r) => r.data)
  },
  remove(id: number) {
    return api.delete(`/tasks/${id}`)
  },
}

export const statsApi = {
  dashboard() {
    return api.get<DashboardStats>('/statistics/dashboard').then((r) => r.data)
  },
}

export const riskApi = {
  listByProject(projectId: number, params?: Record<string, unknown>) {
    return api.get<Risk[]>(`/projects/${projectId}/risks`, { params }).then((r) => r.data)
  },
  create(projectId: number, payload: Partial<Risk>) {
    return api.post<Risk>(`/projects/${projectId}/risks`, payload).then((r) => r.data)
  },
  update(id: number, payload: Partial<Risk>) {
    return api.put<Risk>(`/risks/${id}`, payload).then((r) => r.data)
  },
  remove(id: number) {
    return api.delete(`/risks/${id}`)
  },
}

export const userApi = {
  me() {
    return api.get<User>('/users/me').then((r) => r.data)
  },
  list(params?: Record<string, unknown>) {
    return api.get<User[]>('/users', { params }).then((r) => r.data)
  },
  update(id: number, payload: Partial<User>) {
    return api.put<User>(`/users/${id}`, payload).then((r) => r.data)
  },
  updateRole(id: number, role: string) {
    return api.patch<User>(`/users/${id}/role`, { role }).then((r) => r.data)
  },
}

export const departmentApi = {
  list(params?: Record<string, unknown>) {
    return api.get<Department[]>('/departments/', { params }).then((r) => r.data)
  },
  create(payload: Partial<Department>) {
    return api.post<Department>('/departments/', payload).then((r) => r.data)
  },
  update(id: number, payload: Partial<Department>) {
    return api.put<Department>(`/departments/${id}`, payload).then((r) => r.data)
  },
  remove(id: number) {
    return api.delete(`/departments/${id}`)
  },
}

export const settingsApi = {
  getMeeting() {
    return api.get<MeetingState>('/settings/meeting').then((r) => r.data)
  },
  setMeetingActive(active: boolean) {
    return api.put<MeetingState>('/settings/meeting/active', { active }).then((r) => r.data)
  },
  setMeetingCount(count: number) {
    return api.put<MeetingState>('/settings/meeting/count', { count }).then((r) => r.data)
  },
  getFollowupStallDays() {
    return api.get<{ days: number }>('/settings/followup-stall-days').then((r) => r.data)
  },
  setFollowupStallDays(days: number) {
    return api.put<{ days: number }>('/settings/followup-stall-days', { days }).then((r) => r.data)
  },
  getCoreGroupChatId() {
    return api.get<{ chat_id: string }>('/settings/core-group-chat-id').then((r) => r.data)
  },
  setCoreGroupChatId(chat_id: string) {
    return api.put<{ chat_id: string }>('/settings/core-group-chat-id', { chat_id }).then((r) => r.data)
  },
  getAutoOpenMeeting() {
    return api.get<{ enabled: boolean }>('/settings/auto-open-meeting').then((r) => r.data)
  },
  setAutoOpenMeeting(enabled: boolean) {
    return api.put<{ enabled: boolean }>('/settings/auto-open-meeting', { enabled }).then((r) => r.data)
  },
  exportBackup() {
    return api.get('/backup/export', { responseType: 'blob' })
  },
  importBackup(file: File) {
    const form = new FormData()
    form.append('file', file)
    return api.post<{ message: string; counts: Record<string, number> }>(
      '/backup/import', form,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    ).then((r) => r.data)
  },
}

export const meetingApi = {
  sessions() {
    return api.get<MeetingSessions>('/meeting-records/sessions').then((r) => r.data)
  },
  detail(session: number) {
    return api.get<MeetingRecordDetail>(`/meeting-records/${session}`).then((r) => r.data)
  },
  open(payload: { session: number; recorder?: string | null; meeting_date: string }) {
    return api.post<MeetingRecordDetail>('/meeting-records/open', payload).then((r) => r.data)
  },
  close() {
    return api.post<MeetingState>('/meeting-records/close').then((r) => r.data)
  },
  send(session: number) {
    return api.post<MeetingSendResult>(`/meeting-records/${session}/send`).then((r) => r.data)
  },
}
