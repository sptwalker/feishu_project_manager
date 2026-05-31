import api from './client'
import type { Project, Task, Risk, User, Department, DashboardStats, MeetingState } from '@/types'

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
  importExcel(file: File) {
    const form = new FormData()
    form.append('file', file)
    return api.post<{ created: number; error_count: number; errors: unknown[] }>(
      '/reports/projects/import', form,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    ).then((r) => r.data)
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
}
