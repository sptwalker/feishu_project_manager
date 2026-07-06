import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useBrandingStore } from '@/stores/branding'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/auth/callback',
      name: 'auth-callback',
      component: () => import('@/views/AuthCallbackView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/layouts/AppLayout.vue'),
      children: [
        { path: '', redirect: '/board' },
        { path: 'board', name: 'board', component: () => import('@/views/ProjectBoardView.vue') },
        { path: 'overview', name: 'overview', component: () => import('@/views/ProjectOverviewView.vue') },
        {
          path: 'projects/:id/tasks',
          name: 'project-tasks',
          component: () => import('@/views/TaskBoardView.vue'),
          props: true,
        },
        {
          path: 'projects/:id/risks',
          name: 'project-risks',
          component: () => import('@/views/RiskBoardView.vue'),
          props: true,
        },
        { path: 'settings', name: 'settings', component: () => import('@/views/SettingsView.vue') },
        { path: 'sales-codes', name: 'sales-codes', component: () => import('@/views/SalesCodesView.vue') },
      ],
    },
    {
      // 周会汇报页：独立顶层路由（不套 AppLayout 侧边栏，全屏汇报模式）
      path: '/meeting-report',
      name: 'meeting-report',
      component: () => import('@/views/MeetingReportView.vue'),
    },
  ],
})

// 路由守卫：未登录访问非 public 页 -> 跳登录
router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && auth.isAuthenticated) {
    return { name: 'board' }
  }
  // 内部销售码：仅 sales 租户实例可访问（部署级开关经 /branding 下发；管理员闸靠菜单隐藏 + 后端鉴权）
  if (to.name === 'sales-codes' && !useBrandingStore().data.sales_code_enabled) {
    return { name: 'board' }
  }
})

export default router
