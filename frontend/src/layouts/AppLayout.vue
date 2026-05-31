<template>
  <div class="shell">
    <!-- 左侧导航 -->
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-mark">飞</span>
        <span class="brand-name">飞书<span class="brand-accent">PM</span></span>
      </div>

      <nav class="nav">
        <RouterLink to="/board" class="nav-item" active-class="active">
          <el-icon><Grid /></el-icon><span>项目看板</span>
        </RouterLink>
        <RouterLink to="/overview" class="nav-item" active-class="active">
          <el-icon><Tickets /></el-icon><span>项目总览</span>
        </RouterLink>
        <RouterLink to="/users" class="nav-item" active-class="active">
          <el-icon><User /></el-icon><span>用户管理</span>
        </RouterLink>
        <div class="nav-item disabled">
          <el-icon><Warning /></el-icon><span>风险</span>
        </div>
        <div class="nav-item disabled">
          <el-icon><DataAnalysis /></el-icon><span>报表</span>
        </div>
      </nav>

      <div class="nav-foot">
        <RouterLink to="/settings" class="nav-item" active-class="active">
          <el-icon><Setting /></el-icon><span>设置</span>
        </RouterLink>
      </div>
    </aside>

    <!-- 右侧主区 -->
    <div class="main">
      <header class="topbar">
        <div class="crumb">
          <slot name="crumb">项目管理</slot>
        </div>
        <div class="top-actions">
          <el-dropdown trigger="click" @command="onCommand">
            <span class="user">
              <span class="uname">{{ userName }}</span>
              <span class="avatar">{{ initial }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="settings">个人设置</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <main class="content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const userName = computed(() => auth.currentUser?.name ?? '')
const initial = computed(() => (auth.currentUser?.name ? auth.currentUser.name.slice(0, 1) : '我'))

function onCommand(cmd: string) {
  if (cmd === 'logout') {
    auth.logout()
    router.replace({ name: 'login' })
  } else if (cmd === 'settings') {
    router.push({ name: 'settings' })
  }
}

onMounted(() => {
  if (!auth.currentUser) auth.fetchCurrentUser()
})
</script>

<style scoped>
.shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* 侧栏 */
.sidebar {
  width: var(--sidebar-w);
  flex-shrink: 0;
  background: var(--c-sidebar);
  color: var(--c-on-dark);
  display: flex;
  flex-direction: column;
  padding: var(--sp-5) var(--sp-3);
}
.brand {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  padding: 0 var(--sp-2) var(--sp-6);
}
.brand-mark {
  width: 34px; height: 34px;
  display: grid; place-items: center;
  background: var(--c-accent);
  color: #fff;
  border-radius: var(--r-md);
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 17px;
}
.brand-name {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 18px;
  letter-spacing: -0.02em;
}
.brand-accent { color: var(--c-accent); margin-left: 2px; }

.nav { display: flex; flex-direction: column; gap: 2px; flex: 1; }
.nav-foot { padding-top: var(--sp-3); border-top: 1px solid var(--c-sidebar-hover); }

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  padding: 10px var(--sp-3);
  border-radius: var(--r-sm);
  color: var(--c-on-dark-dim);
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.nav-item:hover { background: var(--c-sidebar-hover); color: var(--c-on-dark); }
.nav-item.active {
  background: var(--c-accent);
  color: #fff;
}
.nav-item.disabled { opacity: 0.4; cursor: not-allowed; }
.nav-item.disabled:hover { background: transparent; color: var(--c-on-dark-dim); }

/* 主区 */
.main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.topbar {
  height: var(--topbar-h);
  flex-shrink: 0;
  background: var(--c-surface);
  border-bottom: 1px solid var(--c-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--sp-6);
}
.crumb { font-family: var(--font-display); font-weight: 600; color: var(--c-ink-2); }
.user { display: flex; align-items: center; gap: var(--sp-2); cursor: pointer; color: var(--c-ink-2); }
.uname { font-weight: 600; font-size: 13px; color: var(--c-ink-2); }
.avatar {
  width: 32px; height: 32px;
  display: grid; place-items: center;
  background: var(--c-accent-soft);
  color: var(--c-accent);
  border-radius: 50%;
  font-weight: 600;
}
.content { flex: 1; overflow-y: auto; }
</style>
