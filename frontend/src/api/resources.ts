import api from './client'
import type { Project, Task, Risk, User, Department, DashboardStats, MeetingState, MeetingRecordDetail, MeetingSessions, MeetingSendResult, OperationLog, MeetingReportOrder, MeetingTimerSettings, TimerState, AtRiskOwner, FollowupAuto, ImageItem } from '@/types'

/* 图片上传：进展配图（JPG/PNG ≤10MB）。返回 {url, name, size} */
export const uploadApi = {
  image(file: File) {
    const form = new FormData()
    form.append('file', file)
    return api.post<ImageItem>('/uploads/image', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data)
  },
}

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
  // 项目历史修改记录（操作日志，按项目过滤）
  history(id: number) {
    return api.get<OperationLog[]>(`/projects/${id}/history`).then((r) => r.data)
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
  setStatus(id: number, status: string) {
    return api.patch<User>(`/users/${id}/status`, { status }).then((r) => r.data)
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
  getAutoReminder() {
    return api.get<{ enabled: boolean }>('/settings/auto-reminder').then((r) => r.data)
  },
  setAutoReminder(enabled: boolean) {
    return api.put<{ enabled: boolean }>('/settings/auto-reminder', { enabled }).then((r) => r.data)
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
  getMeetingReportOrder() {
    return api.get<MeetingReportOrder>('/settings/meeting-report-order').then((r) => r.data)
  },
  setMeetingReportOrder(order: MeetingReportOrder) {
    return api.put<MeetingReportOrder>('/settings/meeting-report-order', order).then((r) => r.data)
  },
  getMeetingTimer() {
    return api.get<MeetingTimerSettings>('/settings/meeting-timer').then((r) => r.data)
  },
  setMeetingTimer(payload: MeetingTimerSettings) {
    return api.put<MeetingTimerSettings>('/settings/meeting-timer', payload).then((r) => r.data)
  },
  getFeishuApp() {
    return api.get<{ app_id: string; secret_set: boolean }>('/settings/feishu-app').then((r) => r.data)
  },
  setFeishuApp(payload: { app_id: string; app_secret?: string | null }) {
    return api.put<{ app_id: string; secret_set: boolean }>('/settings/feishu-app', payload).then((r) => r.data)
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
  close(clientId?: string) {
    return api.post<MeetingState>('/meeting-records/close', { client_id: clientId ?? null }).then((r) => r.data)
  },
  send(session: number) {
    return api.post<MeetingSendResult>(`/meeting-records/${session}/send`).then((r) => r.data)
  },
  startReport(session: number) {
    return api.post<MeetingRecordDetail>(`/meeting-records/${session}/start-report`).then((r) => r.data)
  },
}

/* 会议服务端计时 + 主控 */
export const timerApi = {
  state(clientId: string) {
    return api.get<TimerState>('/meeting/timer/state', { params: { client_id: clientId } }).then((r) => r.data)
  },
  claim(clientId: string) {
    return api.post<TimerState>('/meeting/timer/claim', { client_id: clientId }).then((r) => r.data)
  },
  heartbeat(clientId: string) {
    return api.post<TimerState>('/meeting/timer/heartbeat', { client_id: clientId }).then((r) => r.data)
  },
  control(clientId: string, action: 'resume' | 'pause' | 'select_presenter', presenterKey?: string | null) {
    return api.post<TimerState>('/meeting/timer/control', { client_id: clientId, action, presenter_key: presenterKey ?? null }).then((r) => r.data)
  },
  takeover(clientId: string, expectedVersion?: number | null) {
    return api.post<TimerState>('/meeting/timer/takeover', { client_id: clientId, expected_version: expectedVersion ?? null }).then((r) => r.data)
  },
}

export const logApi = {
  list(params: { start?: string; end?: string; limit?: number }) {
    return api.get<OperationLog[]>('/operation-logs', { params }).then((r) => r.data)
  },
}

/* 品牌设置（管理员；DB 存、UI 改、免登服务器） */
export interface BrandingFull {
  brand_sidebar: string
  brand_login: string
  brand_mark: string
  page_title: string
  login_headline: string
  login_sub: string
  org_scope: string
  dept_unit: string
  logo_url: string
  favicon_url: string
  accent: string
  accent_hover: string
  accent_soft: string
  sidebar_bg: string
  sidebar_hover: string
}

export const brandingApi = {
  get() {
    return api.get<BrandingFull>('/settings/branding').then((r) => r.data)
  },
  update(payload: Partial<BrandingFull>) {
    return api.put<BrandingFull>('/settings/branding', payload).then((r) => r.data)
  },
}

export const followupApi = {
  atRiskOwners() {
    return api.get<AtRiskOwner[]>('/followup/at-risk-owners').then((r) => r.data)
  },
  notifyOwner(owner_name: string) {
    return api.post<{ sent: boolean; reason?: string | null }>(
      '/followup/notify-owner', { owner_name }).then((r) => r.data)
  },
  getAuto() {
    return api.get<FollowupAuto>('/settings/followup-auto').then((r) => r.data)
  },
  setAuto(cfg: FollowupAuto) {
    return api.put<FollowupAuto>('/settings/followup-auto', cfg).then((r) => r.data)
  },
}
