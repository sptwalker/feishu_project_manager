<template>
  <div class="system-log">
    <section class="card">
      <h3 class="card-title">系统操作日志</h3>
      <p class="tip muted" style="margin-top:0">
        查询时间范围内的用户操作记录（登录、新增/删除项目、更新进展、评论、反馈）。仅管理员可查看。
      </p>

      <template v-if="isAdmin">
        <div class="log-toolbar">
          <el-date-picker
            v-model="range"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DD HH:mm:ss"
            :shortcuts="shortcuts"
            style="width: 420px"
          />
          <el-button type="primary" :icon="Search" :loading="loading" @click="query">查询</el-button>
          <span class="muted hint">共 {{ logs.length }} 条</span>
        </div>

        <div v-loading="loading" class="log-window">
          <div v-if="logs.length" class="log-list">
            <div v-for="log in logs" :key="log.id" class="log-row">
              <span class="log-user">{{ log.user_name || '—' }}</span>
              <span class="log-time num">{{ fmt(log.occurred_at) }}</span>
              <span class="log-desc">{{ log.description }}</span>
            </div>
          </div>
          <el-empty v-else :description="queried ? '该时间范围内暂无操作记录' : '请选择时间范围后点击查询'" :image-size="60" />
        </div>
      </template>

      <el-empty v-else description="仅管理员可查看系统日志" :image-size="60" />
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { logApi } from '@/api/resources'
import type { OperationLog } from '@/types'

const auth = useAuthStore()
const isAdmin = computed(() => auth.currentUser?.role === 'admin')

const range = ref<[string, string] | null>(null)
const logs = ref<OperationLog[]>([])
const loading = ref(false)
const queried = ref(false)

/* 默认范围快捷选项 */
const shortcuts = [
  { text: '今天', value: () => { const e = new Date(); const s = new Date(); s.setHours(0, 0, 0, 0); return [s, e] } },
  { text: '近7天', value: () => { const e = new Date(); const s = new Date(); s.setTime(s.getTime() - 7 * 86400000); return [s, e] } },
  { text: '近30天', value: () => { const e = new Date(); const s = new Date(); s.setTime(s.getTime() - 30 * 86400000); return [s, e] } },
]

function fmt(t: string): string {
  return (t || '').replace('T', ' ').slice(0, 16)
}

async function query() {
  loading.value = true
  try {
    const params: { start?: string; end?: string } = {}
    if (range.value && range.value[0]) params.start = range.value[0]
    if (range.value && range.value[1]) params.end = range.value[1]
    logs.value = await logApi.list(params)
    queried.value = true
  } catch {
    ElMessage.error('查询失败（需要管理员权限）')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.system-log { padding: var(--sp-2) 0; }
.card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  padding: var(--sp-5);
  box-shadow: var(--shadow-sm);
}
.card-title { font-size: 15px; margin-bottom: var(--sp-4); }
.tip { font-size: 12px; line-height: 1.6; margin-bottom: var(--sp-4); }
.hint { font-size: 12px; }

.log-toolbar { display: flex; align-items: center; gap: var(--sp-3); margin-bottom: var(--sp-4); flex-wrap: wrap; }

.log-window {
  min-height: 200px;
  max-height: 56vh;
  overflow-y: auto;
  border: 1px solid var(--c-border);
  border-radius: var(--r-sm);
  background: var(--c-canvas);
  padding: var(--sp-2) 0;
}
.log-list { display: flex; flex-direction: column; }
.log-row {
  display: flex;
  align-items: baseline;
  gap: var(--sp-3);
  padding: 6px var(--sp-4);
  font-size: 13px;
  line-height: 1.6;
  border-bottom: 1px dashed var(--c-border);
}
.log-row:last-child { border-bottom: none; }
.log-user { color: #1a73e8; font-weight: 600; flex-shrink: 0; min-width: 72px; }
.log-time { color: var(--c-ink-3); flex-shrink: 0; }
.log-desc { color: var(--c-ink); }
</style>
