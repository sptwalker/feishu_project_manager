<template>
  <div class="user-management">
    <div class="toolbar">
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
        <el-table-column prop="feishu_user_id" label="飞书ID" min-width="150" show-overflow-tooltip />
        <el-table-column label="最后登录" width="170">
          <template #default="{ row }">
            <span class="muted">{{ fmtDate(row.last_login_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90" align="center">
          <template #default="{ row }">
            <el-button v-if="isAdmin" size="small" text type="primary" @click="openEdit(row)">编辑</el-button>
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
import { roleLabel, ROLE_OPTIONS } from '@/utils/labels'

const auth = useAuthStore()
const users = ref<User[]>([])
const departments = ref<Department[]>([])
const loading = ref(false)
const filterRole = ref<string>('')

const isAdmin = computed(() => auth.currentUser?.role === 'admin')
const roleText = (r: string) => roleLabel[r] ?? r
const initial = (name: string) => (name ? name.slice(0, 1) : '?')

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
    users.value = await userApi.list(params)
  } catch {
    ElMessage.error('加载用户失败')
  } finally {
    loading.value = false
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
})

function openEdit(u: User) {
  editingId.value = u.id
  form.value = {
    name: u.name || '',
    name_en: u.name_en || '',
    position: u.position || '',
    department: u.department || '',
    role: u.role || 'member',
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
    }
    await userApi.update(editingId.value, payload as Partial<User>)
    ElMessage.success('已保存')
    editVisible.value = false
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

:deep(.el-table) { --el-table-border-color: var(--c-border); }
</style>
