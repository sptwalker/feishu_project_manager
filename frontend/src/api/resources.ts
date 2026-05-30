import api from './client'
import type { Project, Task, Risk, DashboardStats } from '@/types'

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
