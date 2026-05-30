<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">系统设置</h1>
        <p class="muted">个人信息与系统概览</p>
      </div>
    </div>

    <!-- 个人信息 -->
    <section class="card">
      <h3 class="card-title">个人信息</h3>
      <div v-if="user" class="profile">
        <span class="big-avatar">{{ initial }}</span>
        <div class="profile-rows">
          <div class="prow"><span class="plabel">姓名</span><span class="pval">{{ user.name }}</span></div>
          <div class="prow"><span class="plabel">角色</span>
            <span class="role-badge" :class="'role-' + user.role">{{ roleText(user.role) }}</span>
          </div>
          <div class="prow"><span class="plabel">部门</span><span class="pval">{{ user.department || '—' }}</span></div>
          <div class="prow"><span class="plabel">飞书ID</span><span class="pval num">{{ user.feishu_user_id }}</span></div>
          <div class="prow"><span class="plabel">最后登录</span><span class="pval muted">{{ fmtDate(user.last_login_at) }}</span></div>
        </div>
      </div>
      <el-empty v-else description="未获取到用户信息" :image-size="60" />
    </section>

    <!-- 系统信息 -->
    <section class="card">
      <h3 class="card-title">系统信息</h3>
      <div class="info-grid">
        <div class="iitem"><span class="plabel">应用</span><span class="pval">飞书项目管理系统</span></div>
        <div class="iitem"><span class="plabel">前端版本</span><span class="pval num">v0.10.0-dev</span></div>
        <div class="iitem"><span class="plabel">技术栈</span><span class="pval">Vue 3 · Element Plus · Pinia · ECharts</span></div>
        <div class="iitem"><span class="plabel">后端</span><span class="pval">FastAPI · SQLAlchemy · 飞书 OAuth</span></div>
      </div>
    </section>

    <section class="card">
      <h3 class="card-title">账号</h3>
      <el-button type="danger" plain @click="logout">退出登录</el-button>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { User } from '@/types'
import { roleLabel } from '@/utils/labels'

const auth = useAuthStore()
const router = useRouter()
const user = ref<User | null>(auth.currentUser)

const initial = computed(() => (user.value?.name ? user.value.name.slice(0, 1) : '我'))
const roleText = (r: string) => roleLabel[r] ?? r

function fmtDate(s?: string | null) {
  if (!s) return '从未登录'
  return new Date(s).toLocaleString('zh-CN', { hour12: false })
}

function logout() {
  auth.logout()
  router.replace({ name: 'login' })
}

onMounted(async () => {
  if (!user.value) {
    user.value = await auth.fetchCurrentUser()
  }
})
</script>

<style scoped>
.card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  padding: var(--sp-5);
  margin-bottom: var(--sp-4);
  box-shadow: var(--shadow-sm);
}
.card-title { font-size: 15px; margin-bottom: var(--sp-4); }

.profile { display: flex; gap: var(--sp-5); align-items: start; }
.big-avatar {
  width: 64px; height: 64px; flex-shrink: 0;
  display: grid; place-items: center;
  background: var(--c-accent); color: #fff;
  border-radius: var(--r-lg); font-size: 26px; font-weight: 700;
  font-family: var(--font-display);
}
.profile-rows { flex: 1; display: flex; flex-direction: column; gap: var(--sp-3); }
.prow { display: flex; align-items: center; gap: var(--sp-4); }
.plabel { width: 84px; color: var(--c-ink-3); font-size: 13px; flex-shrink: 0; }
.pval { color: var(--c-ink); font-weight: 500; }

.info-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--sp-4); }
@media (max-width: 600px) { .info-grid { grid-template-columns: 1fr; } }
.iitem { display: flex; flex-direction: column; gap: var(--sp-1); }

.role-badge { font-weight: 600; font-size: 12px; padding: 2px 10px; border-radius: 999px; }
.role-admin { color: var(--c-status-overdue); background: var(--c-status-overdue-soft); }
.role-project_manager { color: var(--c-accent); background: var(--c-accent-soft); }
.role-member { color: var(--c-status-done); background: var(--c-status-done-soft); }
.role-observer { color: var(--c-ink-3); background: var(--c-surface-2); }
</style>
