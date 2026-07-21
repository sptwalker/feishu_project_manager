import api from './client'
import type { Project, Task, Risk, User, Department, DashboardStats, MeetingState, MeetingRecordDetail, MeetingSessions, MeetingSendResult, OperationLog, MeetingReportOrder, MeetingTimerSettings, TimerState, AtRiskOwner, FollowupAuto, ImageItem, SalesCode, SalesCodePrefix, SmtpConfig, DiscussBoardInfo, DiscussAuthResult, DiscussThreadList, DiscussMessage, DiscussAttachment } from '@/types'

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
  // 项目集合变更签名（count:sum(version)）：会议页轮询检测他端改动，变化才重拉列表
  revision() {
    return api.get<{ revision: string }>('/projects/revision').then((r) => r.data.revision)
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
  getSalesCodeEnabled() {
    return api.get<{ enabled: boolean }>('/settings/sales-code-enabled').then((r) => r.data)
  },
  setSalesCodeEnabled(enabled: boolean) {
    return api.put<{ enabled: boolean }>('/settings/sales-code-enabled', { enabled }).then((r) => r.data)
  },
  // 留言讨论区：开关 + SMTP 配置
  getDiscussEnabled() {
    return api.get<{ enabled: boolean }>('/settings/discuss-enabled').then((r) => r.data)
  },
  setDiscussEnabled(enabled: boolean) {
    return api.put<{ enabled: boolean }>('/settings/discuss-enabled', { enabled }).then((r) => r.data)
  },
  getSmtp() {
    return api.get<SmtpConfig>('/settings/smtp').then((r) => r.data)
  },
  setSmtp(payload: Partial<SmtpConfig> & { password?: string }) {
    return api.put<SmtpConfig>('/settings/smtp', payload).then((r) => r.data)
  },
  testSmtp(to: string) {
    return api.post<{ ok: boolean; message: string }>('/settings/smtp/test', { to }).then((r) => r.data)
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
  /* 从 Excel（周会跟进清单格式）批量导入项目：按行新增（追加，不替换现有数据）。
     返回 created=成功数, errors=逐行错误, error_count=出错行数。 */
  importProjectsExcel(file: File) {
    const form = new FormData()
    form.append('file', file)
    return api.post<{ created: number; errors: { row: number; error: string }[]; error_count: number }>(
      '/reports/projects/import', form,
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

/* 内部销售码管理（管理员；sales 租户）。核销失败原因由后端返回 */
export interface RedeemResult {
  ok: boolean
  reason: string
  record?: SalesCode | null
}
export interface BatchRedeemResponse {
  redeemed: SalesCode[]
  failed: { code: string; reason: string }[]
}

export const salesCodeApi = {
  generate(payload: { count: number; prefix: string; issued_to: string; password: string }) {
    return api.post<SalesCode[]>('/sales-codes/generate', payload).then((r) => r.data)
  },
  redeem(code: string) {
    return api.post<RedeemResult>('/sales-codes/redeem', { code }).then((r) => r.data)
  },
  redeemBatch(codes: string[]) {
    return api.post<BatchRedeemResponse>('/sales-codes/redeem-batch', { codes }).then((r) => r.data)
  },
  query(params: { code?: string; prefix?: string; start?: string; end?: string; redeemed?: boolean }) {
    return api.get<SalesCode[]>('/sales-codes', { params }).then((r) => r.data)
  },
  getPwdStatus() {
    return api.get<{ is_default: boolean }>('/sales-codes/gen-password/status').then((r) => r.data)
  },
  setPwd(password: string) {
    return api.put<{ is_default: boolean }>('/sales-codes/gen-password', { password }).then((r) => r.data)
  },
  listPrefixes() {
    return api.get<SalesCodePrefix[]>('/sales-codes/prefixes').then((r) => r.data)
  },
  createPrefix(payload: { prefix: string; remark: string; max_count?: number | null }) {
    return api.post<SalesCodePrefix>('/sales-codes/prefixes', payload).then((r) => r.data)
  },
  setPrefixDisabled(id: number, disabled: boolean) {
    return api.put<SalesCodePrefix>(`/sales-codes/prefixes/${id}`, { disabled }).then((r) => r.data)
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

/* ---------- 留言讨论区 ----------
   公开端（外部用户）：独立 token 存 localStorage 'dsc_token'（与内部 fpm_access_token 完全隔离），
   用原生 fetch 携带，不走 axios 实例（其拦截器会注入内部 token）。
   管理端（内部用户）：走现有 api 实例（内部 JWT）。 */
const DSC_TOKEN_KEY = 'dsc_token'

export const discussTokenStore = {
  get(): string { return localStorage.getItem(DSC_TOKEN_KEY) || '' },
  set(t: string) { localStorage.setItem(DSC_TOKEN_KEY, t) },
  clear() { localStorage.removeItem(DSC_TOKEN_KEY) },
}

async function dscFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { ...(init?.headers as Record<string, string> | undefined) }
  const token = discussTokenStore.get()
  if (token) headers['Authorization'] = `Bearer ${token}`
  const resp = await fetch(`/api/v1${path}`, { ...init, headers })
  const data = await resp.json().catch(() => ({}))
  if (!resp.ok) throw Object.assign(new Error(data.detail || '请求失败'), { status: resp.status, detail: data.detail })
  return data as T
}

export const discussApi = {
  /* --- 公开端 --- */
  board() {
    return dscFetch<DiscussBoardInfo>('/discuss/board')
  },
  requestCode(email: string) {
    return dscFetch<{ ok: boolean }>('/discuss/code', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, website: '' }),
    })
  },
  register(payload: { email: string; code: string; nickname: string; phone: string }) {
    return dscFetch<DiscussAuthResult>('/discuss/register', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...payload, website: '' }),
    })
  },
  login(payload: { email: string; code: string }) {
    return dscFetch<DiscussAuthResult>('/discuss/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  },
  threads(page = 1, size = 10) {
    return dscFetch<DiscussThreadList>(`/discuss/threads?page=${page}&size=${size}`)
  },
  postMessage(payload: { content: string; thread_id?: number | null; attachments?: DiscussAttachment[] }) {
    return dscFetch<DiscussMessage>('/discuss/messages', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  },
  upload(file: File) {
    const form = new FormData()
    form.append('file', file)
    return dscFetch<DiscussAttachment>('/discuss/upload', { method: 'POST', body: form })
  },
  /* --- 管理端（内部 JWT） --- */
  adminThreads(params: { page?: number; size?: number; keyword?: string; only_unreplied?: boolean; min_star?: number }) {
    return api.get<DiscussThreadList>('/discuss/admin/threads', { params }).then((r) => r.data)
  },
  adminReply(thread_id: number, content: string) {
    return api.post<DiscussMessage>('/discuss/admin/reply', { thread_id, content }).then((r) => r.data)
  },
  /* 设置公告（PMS 管理员；内部 JWT）。公开页顶部展示。 */
  setAnnouncement(content: string) {
    return api.put<{ content: string }>('/discuss/admin/announcement', { content }).then((r) => r.data)
  },
  adminStar(message_id: number, star: number) {
    return api.put<{ id: number; star: number }>('/discuss/admin/star', { message_id, star }).then((r) => r.data)
  },
  adminVisibility(message_id: number, visible: boolean) {
    return api.put<{ id: number; status: string }>('/discuss/admin/visibility', { message_id, visible }).then((r) => r.data)
  },
  adminBlock(ext_user_id: number, blocked: boolean) {
    return api.put<{ id: number; status: string }>('/discuss/admin/block', { ext_user_id, blocked }).then((r) => r.data)
  },
  adminDeleteThread(thread_id: number) {
    return api.delete<{ ok: boolean }>(`/discuss/admin/threads/${thread_id}`).then((r) => r.data)
  },
}
