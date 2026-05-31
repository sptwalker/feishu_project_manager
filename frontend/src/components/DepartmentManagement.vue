<template>
  <div class="department-management">
    <div class="toolbar">
      <span></span>
      <el-button type="primary" :icon="Plus" @click="openCreate">新增部门</el-button>
    </div>

    <div v-loading="loading">
      <el-table :data="departments" stripe style="width: 100%">
        <el-table-column prop="name" label="部门名称" min-width="180">
          <template #default="{ row }">
            <span :style="{ color: row.color || 'inherit', fontWeight: 600 }">
              {{ row.name }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="short_name" label="简称" width="120">
          <template #default="{ row }">
            <span :style="{ color: row.color || 'inherit', fontWeight: 600 }">
              {{ row.short_name || '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="leader" label="负责人" width="140">
          <template #default="{ row }">{{ row.leader || '—' }}</template>
        </el-table-column>
        <el-table-column prop="responsibility" label="部门职责" min-width="280">
          <template #default="{ row }">{{ row.responsibility || '—' }}</template>
        </el-table-column>
        <el-table-column label="颜色" width="120">
          <template #default="{ row }">
            <div v-if="row.color" class="color-preview">
              <span class="color-dot" :style="{ background: row.color }"></span>
              <span class="color-code">{{ row.color }}</span>
            </div>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="right">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" text type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 新增/编辑部门对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑部门' : '新增部门'" width="480px">
      <el-form :model="form" label-width="92px" label-position="left">
        <el-form-item label="部门名称" required>
          <el-input v-model="form.name" placeholder="请输入部门名称" />
        </el-form-item>
        <el-form-item label="部门简称">
          <el-input v-model="form.short_name" placeholder="部门简称（可选）" />
        </el-form-item>
        <el-form-item label="负责人">
          <el-input v-model="form.leader" placeholder="负责人姓名（可选）" />
        </el-form-item>
        <el-form-item label="部门职责">
          <el-input
            v-model="form.responsibility"
            type="textarea"
            :rows="3"
            placeholder="部门职责描述（可选）"
          />
        </el-form-item>
        <el-form-item label="字体颜色">
          <div class="color-picker-wrapper">
            <el-color-picker v-model="form.color" show-alpha :predefine="predefineColors" />
            <el-input v-model="form.color" placeholder="颜色代码（可选）" style="flex: 1; margin-left: var(--sp-2)" />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">{{ isEdit ? '保存' : '创建' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { departmentApi } from '@/api/resources'
import type { Department } from '@/types'

const departments = ref<Department[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const saving = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)

const form = ref({
  name: '',
  short_name: '',
  leader: '',
  responsibility: '',
  color: '',
})

const predefineColors = [
  '#1890ff',
  '#52c41a',
  '#faad14',
  '#f5222d',
  '#722ed1',
  '#13c2c2',
  '#eb2f96',
  '#fa8c16',
  '#2f54eb',
  '#a0d911',
]

async function load() {
  loading.value = true
  try {
    departments.value = await departmentApi.list({ limit: 100 })
  } catch {
    ElMessage.error('加载部门失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  isEdit.value = false
  editingId.value = null
  form.value = {
    name: '',
    short_name: '',
    leader: '',
    responsibility: '',
    color: '',
  }
  dialogVisible.value = true
}

function openEdit(dept: Department) {
  isEdit.value = true
  editingId.value = dept.id
  form.value = {
    name: dept.name,
    short_name: dept.short_name || '',
    leader: dept.leader || '',
    responsibility: dept.responsibility || '',
    color: dept.color || '',
  }
  dialogVisible.value = true
}

async function submit() {
  if (!form.value.name) {
    ElMessage.warning('请填写部门名称')
    return
  }
  saving.value = true
  try {
    const payload: Record<string, unknown> = { ...form.value }
    if (!payload.short_name) delete payload.short_name
    if (!payload.leader) delete payload.leader
    if (!payload.responsibility) delete payload.responsibility
    if (!payload.color) delete payload.color

    if (isEdit.value && editingId.value) {
      await departmentApi.update(editingId.value, payload as Partial<Department>)
      ElMessage.success('部门已更新')
    } else {
      await departmentApi.create(payload as Partial<Department>)
      ElMessage.success('部门已创建')
    }
    dialogVisible.value = false
    await load()
  } catch {
    ElMessage.error(`${isEdit.value ? '更新' : '创建'}失败（需要管理员权限）`)
  } finally {
    saving.value = false
  }
}

async function remove(dept: Department) {
  try {
    await ElMessageBox.confirm(`确定删除部门「${dept.name}」？此操作不可恢复。`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  try {
    await departmentApi.remove(dept.id)
    ElMessage.success('已删除')
    await load()
  } catch {
    ElMessage.error('删除失败（需要管理员权限）')
  }
}

onMounted(load)
</script>

<style scoped>
.department-management {
  padding: var(--sp-2) 0;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--sp-4);
}

.color-preview {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
}

.color-dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1px solid var(--c-border);
}

.color-code {
  font-size: 12px;
  color: var(--c-ink-2);
  font-family: monospace;
}

.color-picker-wrapper {
  display: flex;
  align-items: center;
  width: 100%;
}

:deep(.el-table) { --el-table-border-color: var(--c-border); }
</style>
