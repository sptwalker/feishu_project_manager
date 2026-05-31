<template>
  <el-dialog
    :model-value="visible"
    :title="`周会自动记录 · 第 ${session} 次`"
    width="720px"
    top="6vh"
    @update:model-value="(v: boolean) => emit('update:visible', v)"
    @open="load"
  >
    <div v-loading="loading" class="mr-body">
      <p class="mr-hint muted">
        自动汇总本次周会（第 {{ session }} 次）各项目的最新进展，按 部门 › 负责人 › 优先级 排序。
      </p>

      <div v-if="records.length" class="mr-list">
        <div v-for="(r, i) in records" :key="i" class="mr-item">
          <div class="mr-head">
            <span class="mr-dept" :style="{ color: r.deptColor }">{{ r.deptShort || '—' }}</span>
            <span class="mr-name">{{ r.name }}</span>
            <span class="mr-owner muted">{{ r.owner || '—' }}</span>
          </div>
          <div class="mr-content">
            <span class="mr-status" :style="{ color: progressColor(r.status) }">【{{ r.status }}】</span>{{ r.content }}
            <span class="mr-time muted">{{ r.time }}</span>
          </div>
        </div>
      </div>
      <el-empty v-else-if="!loading" :description="`本次周会暂无记录（第 ${session} 次）`" />
    </div>

    <template #footer>
      <span class="mr-count muted">共 {{ records.length }} 个项目本次有进展记录</span>
      <el-button @click="emit('update:visible', false)">关闭</el-button>
      <el-button type="primary" :icon="Promotion" @click="onSend">发送会议记录</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Promotion } from '@element-plus/icons-vue'
import { projectApi, departmentApi } from '@/api/resources'
import type { Department } from '@/types'
import { urgencyWeight, progressStatusColor } from '@/utils/labels'

const props = defineProps<{ visible: boolean; session: number }>()
const emit = defineEmits<{ (e: 'update:visible', v: boolean): void }>()

interface RecordRow {
  name: string
  owner: string
  deptShort: string
  deptColor?: string
  status: string
  content: string
  time: string
}

const loading = ref(false)
const records = ref<RecordRow[]>([])

const collator = new Intl.Collator('zh-Hans-CN')
const progressColor = (s?: string) => (s && progressStatusColor[s]) || 'var(--c-ink-3)'

function findDept(depts: Department[], name?: string | null) {
  if (!name) return undefined
  const key = name.trim()
  return depts.find((d) => d.name === key || d.short_name === key)
}

async function load() {
  loading.value = true
  records.value = []
  try {
    const [projects, depts] = await Promise.all([
      projectApi.list({ limit: 500 }),
      departmentApi.list({ limit: 100 }),
    ])
    const rows: (RecordRow & { _dept: string; _urg: number })[] = []
    for (const p of projects) {
      const entries = (p.progress_log ?? []).filter((e) => e.meeting_session === props.session)
      if (!entries.length) continue
      const latest = [...entries].sort((a, b) => (a.time || '').localeCompare(b.time || '')).pop()!
      const dept = findDept(depts, p.department)
      const deptShort = dept?.short_name || ''
      rows.push({
        name: p.name,
        owner: p.owner_name || '',
        deptShort,
        deptColor: dept?.color || undefined,
        status: latest.status || '正常',
        content: latest.content || '',
        time: latest.time || '',
        _dept: deptShort,
        _urg: urgencyWeight[p.urgency] ?? 0,
      })
    }
    // 与项目总览一致：部门简称 › 负责人 › 优先级(重要在前)
    rows.sort((a, b) =>
      collator.compare(a._dept, b._dept)
      || collator.compare(a.owner, b.owner)
      || (b._urg - a._urg),
    )
    records.value = rows
  } catch {
    ElMessage.error('加载周会记录失败')
  } finally {
    loading.value = false
  }
}

function onSend() {
  ElMessage.info('发送会议记录功能开发中')
}
</script>

<style scoped>
.mr-body { max-height: 64vh; overflow-y: auto; }
.mr-hint { margin: 0 0 var(--sp-3); font-size: 13px; }
.mr-list { display: flex; flex-direction: column; gap: var(--sp-3); }
.mr-item {
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  padding: var(--sp-3) var(--sp-4);
  background: var(--c-surface);
}
.mr-head { display: flex; align-items: baseline; gap: var(--sp-3); margin-bottom: 4px; }
.mr-dept { font-weight: 600; font-size: 13px; }
.mr-name { font-weight: 600; color: var(--c-ink); }
.mr-owner { font-size: 12px; }
.mr-content { font-size: 14px; color: var(--c-ink); line-height: 1.6; }
.mr-status { font-weight: 600; }
.mr-time { font-size: 12px; margin-left: var(--sp-2); }
.mr-count { margin-right: auto; font-size: 12px; }
:deep(.el-dialog__footer) { display: flex; align-items: center; }
</style>
