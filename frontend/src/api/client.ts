import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'

const ACCESS_KEY = 'fpm_access_token'
const REFRESH_KEY = 'fpm_refresh_token'

export const tokenStore = {
  get access() { return localStorage.getItem(ACCESS_KEY) },
  get refresh() { return localStorage.getItem(REFRESH_KEY) },
  set(access: string, refresh?: string) {
    localStorage.setItem(ACCESS_KEY, access)
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 20000,
})

// 请求拦截：注入 JWT
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStore.access
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：401 时尝试刷新一次，失败则跳登录
let refreshing: Promise<string | null> | null = null

async function tryRefresh(): Promise<string | null> {
  const refresh = tokenStore.refresh
  if (!refresh) return null
  try {
    const resp = await axios.post('/api/v1/auth/refresh', { refresh_token: refresh })
    const newAccess = resp.data.access_token as string
    tokenStore.set(newAccess, resp.data.refresh_token)
    return newAccess
  } catch {
    return null
  }
}

api.interceptors.response.use(
  (resp) => resp,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retried?: boolean }
    if (error.response?.status === 401 && original && !original._retried) {
      original._retried = true
      if (!refreshing) {
        refreshing = tryRefresh().finally(() => { refreshing = null })
      }
      const newToken = await refreshing
      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`
        return api(original)
      }
      // 刷新失败 -> 清除并跳登录
      tokenStore.clear()
      if (location.pathname !== '/login') {
        location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export default api
