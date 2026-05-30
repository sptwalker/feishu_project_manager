import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

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
        { path: 'users', name: 'users', component: () => import('@/views/UsersView.vue') },
        { path: 'settings', name: 'settings', component: () => import('@/views/SettingsView.vue') },
      ],
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
})

export default router
