<template>
  <el-dialog
    :model-value="modelValue"
    title="立即催办"
    width="760px"
    @update:model-value="(v: boolean) => emit('update:modelValue', v)"
    @open="loadOwners"
  >
    <div class="dlg-head">
      <span class="muted">共 {{ owners.length }} 位负责人需要催办</span>
      <el-button type="primary" size="small" :loading="bulkRunning" :disabled="!resolvableCount" @click="notifyAll">
        全部催办（{{ resolvableCount }}）
      </el-button>
    </div>
    <el-table v-loading="ownersLoading" :data="owners" size="small" border max-height="50vh">
      <el-table-column label="负责人" width="110">
        <template #default="{ row }"><span class="owner">{{ row.owner }}</span></template>
      </el-table-column>
      <el-table-column label="停滞项目">
        <template #default="{ row }">
          <span v-if="row.stalled_count">{{ joinNames(row.stalled) }}（{{ row.stalled_count }}）</span>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="待处理项目">
        <template #default="{ row }">
          <span v-if="row.pending_count">{{ joinNames(row.pending) }}（{{ row.pending_count }}）</span>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" align="center">
        <template #default="{ row }">
          <el-button
            v-if="row.resolvable" size="small" text type="primary"
            :loading="row._sending" :disabled="row._done" @click="notifyOne(row)"
          >催办</el-button>
          <el-tooltip v-else content="该负责人未关联飞书账号，无法私聊催办" placement="top">
            <span class="muted hint">未关联账号</span>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="110" align="center">
        <template #default="{ row }">
          <span v-if="row._done" class="ok">发送完成 √</span>
          <span v-else-if="row._failed" class="fail">{{ row._failReason || '失败' }}</span>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!ownersLoading && !owners.length" description="当前没有需要催办的负责人" :image-size="60" />
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { followupApi } from '@/api/resources'
import type { AtRiskOwner } from '@/types'

defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()

type OwnerRow = AtRiskOwner & { _sending?: boolean; _done?: boolean; _failed?: boolean; _failReason?: string }
const owners = ref<OwnerRow[]>([])
const ownersLoading = ref(false)
const bulkRunning = ref(false)
const resolvableCount = computed(() => owners.value.filter((o) => o.resolvable && !o._done).length)

function joinNames(arr: { name: string }[]): string {
  return arr.map((s) => s.name).join('、')
}

async function loadOwners() {
  ownersLoading.value = true
  try {
    const list = await followupApi.atRiskOwners()
    owners.value = list.map((o) => ({ ...o }))
  } catch {
    ElMessage.error('加载催办名单失败（需要管理员权限）')
  } finally {
    ownersLoading.value = false
  }
}

async function notifyOne(row: OwnerRow): Promise<boolean> {
  row._sending = true
  row._failed = false
  try {
    const r = await followupApi.notifyOwner(row.owner)
    if (r.sent) {
      row._done = true
      return true
    }
    row._failed = true
    row._failReason = r.reason || '未发送'
    return false
  } catch {
    row._failed = true
    row._failReason = '请求失败'
    return false
  } finally {
    row._sending = false
  }
}

async function notifyAll() {
  bulkRunning.value = true
  try {
    for (const row of owners.value) {
      if (!row.resolvable || row._done) continue
      await notifyOne(row)
    }
    ElMessage.success('全部催办已执行')
  } finally {
    bulkRunning.value = false
  }
}
</script>

<style scoped>
.dlg-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--sp-3); }
.owner { font-weight: 600; color: #1a73e8; }
.ok { color: #3DBE7B; font-weight: 600; }
.fail { color: #E5484D; font-size: 12px; }
.hint { font-size: 12px; }
</style>
