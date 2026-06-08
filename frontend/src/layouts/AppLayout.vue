<template>
  <div class="shell">
    <!-- 左侧导航 -->
    <aside class="sidebar" :class="{ collapsed }">
      <div class="brand">
        <img :src="logoUrl" alt="Logo" class="brand-logo" />
        <span class="brand-name"><span class="brand-accent">P</span>roject <span class="brand-accent">M</span>anager</span>
      </div>

      <nav class="nav">
        <RouterLink to="/board" class="nav-item" active-class="active" :title="collapsed ? '项目看板' : undefined">
          <el-icon><Grid /></el-icon><span>项目看板</span>
        </RouterLink>
        <RouterLink to="/overview" class="nav-item" active-class="active" :title="collapsed ? '项目总览' : undefined">
          <el-icon><Tickets /></el-icon><span>项目总览</span>
        </RouterLink>
        <RouterLink to="/settings" class="nav-item" active-class="active" :title="collapsed ? '系统设置' : undefined">
          <el-icon><Setting /></el-icon><span>系统设置</span>
        </RouterLink>
        <div class="nav-item disabled" :title="collapsed ? '风险' : undefined">
          <el-icon><Warning /></el-icon><span>风险</span>
        </div>
        <div class="nav-item disabled" :title="collapsed ? '报表' : undefined">
          <el-icon><DataAnalysis /></el-icon><span>报表</span>
        </div>
      </nav>

      <div class="nav-foot">
        <div class="nav-item" :title="collapsed ? '个人信息' : undefined" @click="onCommand('profile')">
          <el-icon><User /></el-icon><span>个人信息</span>
        </div>
      </div>
    </aside>

    <!-- 右侧主区 -->
    <div class="main">
      <header class="topbar">
        <div class="topbar-left">
          <el-icon class="collapse-btn" :title="collapsed ? '展开侧栏' : '收起侧栏'" @click="toggleSidebar">
            <Expand v-if="collapsed" /><Fold v-else />
          </el-icon>
          <div class="crumb">
            <slot name="crumb">项目管理</slot>
          </div>
        </div>
        <div class="top-actions">
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
            <el-tooltip content="查看周会记录" placement="bottom">
              <el-button class="m-record-btn" :icon="Document" size="small" circle @click="recordVisible = true" />
            </el-tooltip>
            <!-- 进入全屏周会汇报：仅周会模式开启且管理员可见；进行中显示绿色，点击二次确认后进入 -->
            <el-tooltip v-if="isAdmin && meeting.active" content="进入周会汇报（全屏）· 进行中" placement="bottom">
              <el-button class="m-record-btn m-record-live" type="success" :icon="Monitor" size="small" circle @click="enterMeetingReport" />
            </el-tooltip>
          </div>
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
    <MeetingConfirmDialog
      v-model:visible="confirmVisible"
      :default-session="confirmSession"
      @opened="recordVisible = true"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Monitor } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useMeetingStore } from '@/stores/meeting'
import MeetingRecordDialog from '@/components/MeetingRecordDialog.vue'
import MeetingConfirmDialog from '@/components/MeetingConfirmDialog.vue'
import logoUrl from '@/assets/logo.png'

const router = useRouter()
const auth = useAuthStore()
const meeting = useMeetingStore()
const recordVisible = ref(false)
const confirmVisible = ref(false)
const confirmSession = ref(1)

// 侧边栏折叠（localStorage 记住偏好）
const collapsed = ref(localStorage.getItem('fpm_sidebar_collapsed') === '1')
function toggleSidebar() {
  collapsed.value = !collapsed.value
  localStorage.setItem('fpm_sidebar_collapsed', collapsed.value ? '1' : '0')
}

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

/* 进入全屏周会汇报页：二次确认后跳转（按钮仅在管理员 + 周会模式开启时可见） */
async function enterMeetingReport() {
  try {
    await ElMessageBox.confirm(
      '要开周会了？是否要进入全屏会议页面？进入后会议即开始计时！',
      '进入周会汇报',
      { type: 'warning', confirmButtonText: '进入', cancelButtonText: '取消' },
    )
  } catch {
    return  // 用户取消
  }
  router.push('/meeting-report')
}

async function onToggleMeeting(val: string | number | boolean) {
  const next = Boolean(val)
  if (next) {
    // 开启：取最新状态，判断是否进入新周期（上次会议日期 + N 天后）
    await meeting.load()
    const st = meeting.state
    const session = st?.next_count ?? st?.calibration_count ?? meeting.currentCount ?? 1
    const newCycle = !!st && !!st.can_open_new_cycle
    if (newCycle) {
      try {
        await ElMessageBox.confirm(
          `上轮周会已经结束超过${st?.new_cycle_days ?? 3}天，现在开启周会模式将进入新的第${session}次周会周期，新周会记录将开启。`,
          '开启新周期周会',
          { type: 'warning', confirmButtonText: '确认开启', cancelButtonText: '取消' },
        )
      } catch {
        return  // 用户取消，开关回弹
      }
    }
    confirmSession.value = session
    confirmVisible.value = true   // 打开信息确认窗（确认后才真正开启）
  } else {
    // 关闭：归档当前周会并关闭模式
    try {
      await meeting.closeMeeting()
      ElMessage.info('已结束本次周会并归档')
    } catch {
      ElMessage.error('操作失败（需要管理员权限）')
    }
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
  transition: width 0.2s ease;
  overflow: hidden;
}
/* 折叠态：只留图标，宽度收窄 */
.sidebar.collapsed { width: 64px; padding-left: var(--sp-2); padding-right: var(--sp-2); }
.sidebar.collapsed .brand { padding-bottom: var(--sp-4); }
.sidebar.collapsed .brand-logo { width: 40px; }
.sidebar.collapsed .brand-name { display: none; }
.sidebar.collapsed .nav-item { justify-content: center; padding-left: 0; padding-right: 0; gap: 0; }
.sidebar.collapsed .nav-item span { display: none; }
.brand {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-2);
  padding: 0 var(--sp-2) var(--sp-6);
}
.brand-logo {
  width: 120px;
  height: auto;
  object-fit: contain;
  display: block;
}
.brand-name {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 22px;
  letter-spacing: -0.02em;
  color: var(--c-on-dark);
  text-align: center;
}
.brand-accent { color: var(--c-accent); }

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
.topbar-left { display: flex; align-items: center; gap: var(--sp-4); }
.collapse-btn { cursor: pointer; font-size: 20px; color: var(--c-ink-3); transition: color 0.15s; }
.collapse-btn:hover { color: var(--c-accent); }
.top-actions { display: flex; align-items: center; gap: var(--sp-4); }
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
/* 全屏汇报「进行中」绿色按钮：轻微呼吸光晕，提示会议进行中 */
.m-record-live { animation: live-pulse 2s ease-in-out infinite; }
@keyframes live-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(26, 127, 75, 0.4); }
  50% { box-shadow: 0 0 0 5px rgba(26, 127, 75, 0); }
}
@media (prefers-reduced-motion: reduce) { .m-record-live { animation: none; } }
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
