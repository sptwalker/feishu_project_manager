<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p class="muted">查看团队成员，管理员可调整角色</p>
      </div>
      <el-select v-model="filterRole" placeholder="全部角色" clearable style="width: 160px" @change="load">
        <el-option v-for="r in ROLE_OPTIONS" :key="r.value" :label="r.label" :value="r.value" />
      </el-select>
    </div>

    <div v-loading="loading">
      <el-table :data="users" stripe style="width: 100%">
        <el-table-column label="成员" min-width="200">
          <template #default="{ row }">
            <div class="member">
              <span class="avatar">{{ initial(row.name) }}</span>
              <div class="member-info">
                <span class="member-name">{{ row.name }}</span>
                <span class="member-dept muted">{{ row.department || '—' }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="160">
          <template #default="{ row }">
            <span class="role-badge" :class="'role-' + row.role">{{ roleText(row.role) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="feishu_user_id" label="飞书ID" min-width="160" />
        <el-table-column label="最后登录" width="180">
          <template #default="{ row }">
            <span class="muted">{{ fmtDate(row.last_login_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" align="right">
          <template #default="{ row }">
            <el-button
              v-if="isAdmin"
              size="small"
              text
              type="primary"
              @click="openRole(row)"
            >
              修改角色
            </el-button>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 修改角色对话框 -->
    <el-dialog v-model="roleVisible" title="修改角色" width="380px">
      <p class="dialog-user">成员：<b>{{ editing?.name }}</b></p>
      <el-select v-model="newRole" style="width: 100%">
        <el-option v-for="r in ROLE_OPTIONS" :key="r.value" :label="r.label" :value="r.value" />
      </el-select>
      <template #footer>
        <el-button @click="roleVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitRole">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { userApi } from '@/api/resources'
import type { User } from '@/types'
import { useAuthStore } from '@/stores/auth'
import { roleLabel, ROLE_OPTIONS } from '@/utils/labels'

const auth = useAuthStore()
const users = ref<User[]>([])
const loading = ref(false)
const filterRole = ref<string>('')

const isAdmin = computed(() => auth.currentUser?.role === 'admin')
const roleText = (r: string) => roleLabel[r] ?? r
const initial = (name: string) => (name ? name.slice(0, 1) : '?')

function fmtDate(s?: string | null) {
  if (!s) return '从未登录'
  return new Date(s).toLocaleString('zh-CN', { hour12: false })
}

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { limit: 200 }
    if (filterRole.value) params.role = filterRole.value
    users.value = await userApi.list(params)
  } catch {
    ElMessage.error('加载用户失败')
  } finally {
    loading.value = false
  }
}

/* 修改角色 */
const roleVisible = ref(false)
const editing = ref<User | null>(null)
const newRole = ref('member')
const saving = ref(false)

function openRole(u: User) {
  editing.value = u
  newRole.value = u.role
  roleVisible.value = true
}

async function submitRole() {
  if (!editing.value) return
  saving.value = true
  try {
    await userApi.updateRole(editing.value.id, newRole.value)
    ElMessage.success('角色已更新')
    roleVisible.value = false
    await load()
  } catch {
    ElMessage.error('更新失败（需要管理员权限）')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.member { display: flex; align-items: center; gap: var(--sp-3); }
.avatar {
  width: 34px; height: 34px; flex-shrink: 0;
  display: grid; place-items: center;
  background: var(--c-accent-soft); color: var(--c-accent);
  border-radius: 50%; font-weight: 600;
}
.member-info { display: flex; flex-direction: column; }
.member-name { font-weight: 600; color: var(--c-ink); }
.member-dept { font-size: 12px; }

.role-badge { font-weight: 600; font-size: 12px; padding: 2px 10px; border-radius: 999px; }
.role-admin { color: var(--c-status-overdue); background: var(--c-status-overdue-soft); }
.role-project_manager { color: var(--c-accent); background: var(--c-accent-soft); }
.role-member { color: var(--c-status-done); background: var(--c-status-done-soft); }
.role-observer { color: var(--c-ink-3); background: var(--c-surface-2); }

.dialog-user { margin: 0 0 var(--sp-4); color: var(--c-ink-2); }
:deep(.el-table) { --el-table-border-color: var(--c-border); }
</style>
