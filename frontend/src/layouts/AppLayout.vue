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
        <RouterLink to="/settings" class="nav-item" active-class="active">
          <el-icon><Setting /></el-icon><span>系统设置</span>
        </RouterLink>
        <div class="nav-item disabled">
          <el-icon><Warning /></el-icon><span>风险</span>
        </div>
        <div class="nav-item disabled">
          <el-icon><DataAnalysis /></el-icon><span>报表</span>
        </div>
      </nav>

      <div class="nav-foot">
        <div class="nav-item" @click="onCommand('profile')">
          <el-icon><User /></el-icon><span>个人信息</span>
        </div>
      </div>
    </aside>

    <!-- 右侧主区 -->
    <div class="main">
      <header class="topbar">
        <div class="topbar-left">
          <div class="crumb">
            <slot name="crumb">项目管理</slot>
          </div>
          <div class="meeting-switch" :class="{ 'is-on': meeting.active }">
            <el-icon class="m-ico"><Calendar /></el-icon>
            <span class="m-label">周例会</span>
            <el-switch
              v-if="isAdmin"
              :model-value="meeting.active"
              @change="onToggleMeeting"
            />
            <span v-else class="m-state" :class="{ on: meeting.active }">
              {{ meeting.active ? '记录中' : '未开启' }}
            </span>
            <el-tooltip v-if="meeting.active" content="周会自动记录" placement="bottom">
              <el-button class="m-record-btn" :icon="Document" size="small" circle @click="recordVisible = true" />
            </el-tooltip>
          </div>
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

    <MeetingRecordDialog v-model:visible="recordVisible" :session="meeting.currentCount" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useMeetingStore } from '@/stores/meeting'
import MeetingRecordDialog from '@/components/MeetingRecordDialog.vue'

const router = useRouter()
const auth = useAuthStore()
const meeting = useMeetingStore()
const recordVisible = ref(false)

const userName = computed(() => auth.currentUser?.name ?? '')
const initial = computed(() => (auth.currentUser?.name ? auth.currentUser.name.slice(0, 1) : '我'))
const isAdmin = computed(() => auth.currentUser?.role === 'admin')

function onCommand(cmd: string) {
  if (cmd === 'logout') {
    auth.logout()
    router.replace({ name: 'login' })
  } else if (cmd === 'settings' || cmd === 'profile') {
    router.push({ name: 'settings' })
  }
}

async function onToggleMeeting(val: string | number | boolean) {
  const next = Boolean(val)
  try {
    await meeting.setActive(next)
    if (next) ElMessage.success('现在进入公司管理周例会记录状态')
    else ElMessage.info('已退出周例会记录状态')
  } catch {
    ElMessage.error('操作失败（需要管理员权限）')
  }
}

onMounted(async () => {
  if (!auth.currentUser) await auth.fetchCurrentUser()
  await meeting.load()
  if (meeting.active && isAdmin.value) {
    ElMessage.info('现在系统在公司周例会记录状态')
  }
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
.topbar-left { display: flex; align-items: center; gap: var(--sp-5); }
.meeting-switch {
  display: flex; align-items: center; gap: var(--sp-2);
  padding: 5px 12px; border-radius: 999px;
  background: var(--c-surface-2); transition: background 0.2s;
}
.meeting-switch.is-on { background: #e8f0fe; }
.m-ico { font-size: 16px; color: var(--c-ink-3); }
.meeting-switch.is-on .m-ico { color: #1a73e8; }
.m-label { font-size: 13px; font-weight: 600; color: var(--c-ink-2); }
.meeting-switch.is-on .m-label { color: #1a73e8; }
.m-state { font-size: 12px; font-weight: 600; color: var(--c-ink-3); }
.m-state.on { color: #1a73e8; }
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
