<template>
  <div class="user-management">
    <div class="toolbar">
      <el-select v-model="filterStatus" placeholder="全部状态" clearable style="width: 150px; margin-right: var(--sp-2)" @change="load">
        <el-option v-for="s in USER_STATUS_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-select v-model="filterRole" placeholder="全部角色" clearable style="width: 160px" @change="load">
        <el-option v-for="r in ROLE_OPTIONS" :key="r.value" :label="r.label" :value="r.value" />
      </el-select>
    </div>

    <div v-loading="loading">
      <el-table :data="users" stripe style="width: 100%">
        <el-table-column label="成员" min-width="150">
          <template #default="{ row }">
            <div class="member">
              <span class="avatar">{{ initial(row.name) }}</span>
              <span class="member-name">{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="name_en" label="英文名" min-width="140">
          <template #default="{ row }">{{ row.name_en || '—' }}</template>
        </el-table-column>
        <el-table-column prop="position" label="职位" width="130">
          <template #default="{ row }">{{ row.position || '—' }}</template>
        </el-table-column>
        <el-table-column prop="department" label="部门" width="120">
          <template #default="{ row }">
            <span :style="{ color: getDepartmentColor(row.department), fontWeight: row.department ? 600 : 400 }">
              {{ row.department || '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="120">
          <template #default="{ row }">
            <span class="role-badge" :class="'role-' + row.role">{{ roleText(row.role) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <span class="status-badge" :class="'status-' + (row.status || 'active')">{{ statusText(row.status) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="feishu_user_id" label="飞书ID" min-width="150" show-overflow-tooltip />
        <el-table-column label="最后登录" width="170">
          <template #default="{ row }">
            <span class="muted">{{ fmtDate(row.last_login_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="center">
          <template #default="{ row }">
            <template v-if="isAdmin">
              <el-button
                v-if="row.status !== 'active'" size="small" text type="success"
                :disabled="row.id === auth.currentUser?.id" @click="setStatus(row, 'active')"
              >{{ row.status === 'pending' ? '通过' : '启用' }}</el-button>
              <el-button
                v-if="row.status === 'active'" size="small" text type="danger"
                :disabled="row.id === auth.currentUser?.id" @click="setStatus(row, 'disabled')"
              >禁用</el-button>
              <el-button size="small" text type="primary" @click="openEdit(row)">编辑</el-button>
            </template>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 编辑用户对话框 -->
    <el-dialog v-model="editVisible" title="编辑用户" width="460px">
      <el-form :model="form" label-width="92px" label-position="left">
        <el-form-item label="中文姓名" required>
          <el-input v-model="form.name" placeholder="中文姓名" />
        </el-form-item>
        <el-form-item label="英文姓名">
          <el-input v-model="form.name_en" placeholder="英文姓名（可选）" />
        </el-form-item>
        <el-form-item label="职位">
          <el-input v-model="form.position" placeholder="职位（可选）" />
        </el-form-item>
        <el-form-item label="所属部门">
          <el-select v-model="form.department" placeholder="选择部门（可选）" clearable filterable style="width: 100%">
            <el-option v-for="dept in departments" :key="dept.id" :label="dept.name" :value="dept.name">
              <span :style="{ color: dept.color || 'inherit', fontWeight: 600 }">{{ dept.name }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="权限角色">
          <el-select v-model="form.role" style="width: 100%">
            <el-option v-for="r in ROLE_OPTIONS" :key="r.value" :label="r.label" :value="r.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="留言区权限">
          <div>
            <p class="muted perm-hint">独立于系统角色，勾选即授权对应操作</p>
            <el-checkbox-group v-model="form.discuss_perms" class="perm-group">
              <el-checkbox v-for="p in DISCUSS_PERM_OPTIONS" :key="p.value" :value="p.value">{{ p.label }}</el-checkbox>
            </el-checkbox-group>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { userApi, departmentApi } from '@/api/resources'
import type { User, Department } from '@/types'
import { useAuthStore } from '@/stores/auth'
import { roleLabel, ROLE_OPTIONS, userStatusLabel, USER_STATUS_OPTIONS } from '@/utils/labels'

const auth = useAuthStore()
const users = ref<User[]>([])
const departments = ref<Department[]>([])
const loading = ref(false)
const filterRole = ref<string>('')
const filterStatus = ref<string>('')

const isAdmin = computed(() => auth.currentUser?.role === 'admin')
const roleText = (r: string) => roleLabel[r] ?? r
const statusText = (s?: string) => userStatusLabel[s || 'active'] ?? (s || 'active')
const initial = (name: string) => (name ? name.slice(0, 1) : '?')

/* 留言区权限项（键与后端 DISCUSS_PERM_KEYS 一致；评星并入「回复」） */
const DISCUSS_PERM_OPTIONS = [
  { value: 'reply', label: '回复 / 评星' },
  { value: 'hide', label: '隐藏 / 恢复' },
  { value: 'delete', label: '删除帖子' },
  { value: 'block', label: '封禁用户' },
  { value: 'announce', label: '发布 / 修改公告' },
]

function getDepartmentColor(deptName?: string | null) {
  if (!deptName) return undefined
  const dept = departments.value.find(d => d.name === deptName)
  return dept?.color || undefined
}

function fmtDate(s?: string | null) {
  if (!s) return '从未登录'
  return new Date(s).toLocaleString('zh-CN', { hour12: false })
}

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { limit: 200 }
    if (filterRole.value) params.role = filterRole.value
    if (filterStatus.value) params.status = filterStatus.value
    let list = await userApi.list(params)
    // 前端按状态筛选（后端 /users 暂未支持 status 过滤），并把待审批用户置顶提醒
    if (filterStatus.value) list = list.filter((u) => (u.status || 'active') === filterStatus.value)
    list.sort((a, b) => (a.status === 'pending' ? -1 : 0) - (b.status === 'pending' ? -1 : 0))
    users.value = list
  } catch {
    ElMessage.error('加载用户失败')
  } finally {
    loading.value = false
  }
}

async function setStatus(u: User, status: string) {
  try {
    await userApi.setStatus(u.id, status)
    ElMessage.success(status === 'active' ? '已启用该用户' : '已禁用该用户')
    await load()
  } catch {
    ElMessage.error('操作失败（需要管理员权限）')
  }
}

async function loadDepartments() {
  try {
    departments.value = await departmentApi.list({ limit: 100 })
  } catch {
    ElMessage.error('加载部门失败')
  }
}

/* 编辑用户：角色 / 职位 / 中英文名 / 部门 */
const editVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = ref({
  name: '',
  name_en: '',
  position: '',
  department: '',
  role: 'member',
  discuss_perms: [] as string[],
})

function openEdit(u: User) {
  editingId.value = u.id
  form.value = {
    name: u.name || '',
    name_en: u.name_en || '',
    position: u.position || '',
    department: u.department || '',
    role: u.role || 'member',
    discuss_perms: [...(u.discuss_perms || [])],
  }
  editVisible.value = true
}

async function submitEdit() {
  if (editingId.value == null) return
  if (!form.value.name.trim()) {
    ElMessage.warning('中文姓名不能为空')
    return
  }
  saving.value = true
  try {
    const payload: Record<string, unknown> = {
      name: form.value.name,
      name_en: form.value.name_en || null,
      position: form.value.position || null,
      department: form.value.department || null,
      role: form.value.role,
      discuss_perms: form.value.discuss_perms,
    }
    await userApi.update(editingId.value, payload as Partial<User>)
    ElMessage.success('已保存')
    editVisible.value = false
    // 若改的是自己，刷新登录态，让菜单/按钮门控立即生效
    if (editingId.value === auth.currentUser?.id) await auth.fetchCurrentUser()
    await load()
  } catch {
    ElMessage.error('保存失败（需要管理员权限）')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  load()
  loadDepartments()
})
</script>

<style scoped>
.user-management {
  padding: var(--sp-2) 0;
}

.toolbar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-bottom: var(--sp-4);
}

.member { display: flex; align-items: center; gap: var(--sp-3); }
.avatar {
  width: 34px; height: 34px; flex-shrink: 0;
  display: grid; place-items: center;
  background: var(--c-accent-soft); color: var(--c-accent);
  border-radius: 50%; font-weight: 600;
}
.member-name { font-weight: 600; color: var(--c-ink); }

.role-badge { font-weight: 600; font-size: 12px; padding: 2px 10px; border-radius: 999px; }
.role-admin { color: var(--c-status-overdue); background: var(--c-status-overdue-soft); }
.role-project_manager { color: var(--c-accent); background: var(--c-accent-soft); }
.role-member { color: var(--c-status-done); background: var(--c-status-done-soft); }
.role-observer { color: var(--c-ink-3); background: var(--c-surface-2); }

.status-badge { font-weight: 600; font-size: 12px; padding: 2px 10px; border-radius: 999px; }
.status-pending { color: #E6A23C; background: #fdf6ec; }
.status-active { color: var(--c-status-done); background: var(--c-status-done-soft); }
.status-disabled { color: var(--c-ink-3); background: var(--c-surface-2); }

:deep(.el-table) { --el-table-border-color: var(--c-border); }

.perm-hint { font-size: 12px; margin: 0 0 6px; }
.perm-group { display: flex; flex-wrap: wrap; gap: 4px 18px; }
</style>
