<template>
  <el-dialog
    :model-value="visible"
    width="820px"
    top="6vh"
    @update:model-value="(v: boolean) => emit('update:visible', v)"
    @open="onOpen"
  >
    <!-- 标题行：次数两侧翻页 -->
    <template #header>
      <div class="mr-title">
        <el-button-group class="mr-pager">
          <el-button :icon="DArrowLeft" :disabled="!canPrev" size="small" title="第一次" @click="goFirst" />
          <el-button :icon="ArrowLeft" :disabled="!canPrev" size="small" title="上一次" @click="goPrev" />
        </el-button-group>
        <span class="mr-title-text">周会记录 · 第 {{ viewingSession }} 次</span>
        <el-button-group class="mr-pager">
          <el-button :icon="ArrowRight" :disabled="!canNext" size="small" title="下一次" @click="goNext" />
          <el-button :icon="DArrowRight" :disabled="!canNext" size="small" title="最后一次" @click="goLast" />
        </el-button-group>
      </div>
    </template>

    <!-- 固定信息区（不随列表滚动）：左侧时间/记录人，右侧排序说明 -->
    <div class="mr-info-row">
      <p class="mr-meta">
        本周周会时间：<b>{{ detail?.meeting_date || '—' }}</b>，
        记录人：<b>{{ detail?.recorder || '—' }}</b>
      </p>
      <p class="mr-hint muted">
        本次周会各项目最新进展，按 部门 › 负责人 › 优先级 排序。
      </p>
    </div>

    <div v-loading="loading" class="mr-body">
      <div v-if="items.length" class="mr-list">
        <div v-for="(r, i) in items" :key="i" class="mr-item">
          <div class="mr-head">
            <span class="mr-dept" :style="{ color: r.dept_color || undefined }">{{ r.dept_short || '—' }}</span>
            <span class="mr-name">{{ r.project }}</span>
            <span class="mr-owner muted">{{ r.owner || '—' }}</span>
          </div>
          <div class="mr-content">
            <span class="mr-status" :style="{ color: progressColor(r.status) }">【{{ r.status }}】</span>{{ r.content }}
            <span class="mr-time muted">{{ r.time }}</span>
          </div>
        </div>
      </div>
      <el-empty v-else-if="!loading" :description="`本次周会暂无记录（第 ${viewingSession} 次）`" />
    </div>

    <template #footer>
      <div class="mr-footer">
        <span class="mr-count muted">共 {{ items.length }} 个项目本次有进展记录</span>
        <span class="mr-actions">
          <el-button @click="emit('update:visible', false)">关闭</el-button>
          <el-button type="primary" :icon="Promotion" :loading="sending" @click="onSend">发送会议记录</el-button>
        </span>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Promotion, ArrowLeft, ArrowRight, DArrowLeft, DArrowRight } from '@element-plus/icons-vue'
import { meetingApi } from '@/api/resources'
import type { MeetingRecordDetail, MeetingItem } from '@/types'
import { progressStatusColor } from '@/utils/labels'

const props = defineProps<{ visible: boolean; session: number }>()
const emit = defineEmits<{ (e: 'update:visible', v: boolean): void }>()

const loading = ref(false)
const sending = ref(false)
const detail = ref<MeetingRecordDetail | null>(null)
const sessions = ref<number[]>([])
const viewingSession = ref(props.session || 1)

const items = computed<MeetingItem[]>(() => detail.value?.items ?? [])
const progressColor = (s?: string) => (s && progressStatusColor[s]) || 'var(--c-ink-3)'

const idx = computed(() => sessions.value.indexOf(viewingSession.value))
const canPrev = computed(() => idx.value > 0)
const canNext = computed(() => idx.value >= 0 && idx.value < sessions.value.length - 1)

async function onOpen() {
  // 打开时拉取翻页边界，默认定位到当前次数（无则末次）
  try {
    const s = await meetingApi.sessions()
    sessions.value = s.sessions
    viewingSession.value = s.sessions.includes(props.session) ? props.session
      : (s.current || s.sessions[s.sessions.length - 1] || 1)
  } catch {
    sessions.value = [props.session || 1]
    viewingSession.value = props.session || 1
  }
  await loadDetail()
}

async function loadDetail() {
  loading.value = true
  detail.value = null
  try {
    detail.value = await meetingApi.detail(viewingSession.value)
  } catch {
    ElMessage.error('加载周会记录失败')
  } finally {
    loading.value = false
  }
}

function goFirst() { if (canPrev.value) { viewingSession.value = sessions.value[0]; loadDetail() } }
function goPrev() { if (canPrev.value) { viewingSession.value = sessions.value[idx.value - 1]; loadDetail() } }
function goNext() { if (canNext.value) { viewingSession.value = sessions.value[idx.value + 1]; loadDetail() } }
function goLast() { if (canNext.value) { viewingSession.value = sessions.value[sessions.value.length - 1]; loadDetail() } }

async function onSend() {
  if (!items.value.length) {
    ElMessage.warning('本次周会暂无记录，无法发送')
    return
  }
  sending.value = true
  try {
    const res = await meetingApi.send(viewingSession.value)
    if (res.ok) {
      ElMessage.success(res.message || '已发送')
      await loadDetail()
    } else {
      ElMessage.warning(res.message || '发送未完成')
    }
  } catch {
    ElMessage.error('发送失败（需要管理员权限）')
  } finally {
    sending.value = false
  }
}
</script>

<style scoped>
.mr-title { display: flex; align-items: center; justify-content: center; gap: var(--sp-3); }
.mr-title-text { font-size: 20px; font-weight: 600; line-height: 2; min-width: 180px; text-align: center; }
.mr-pager { flex-shrink: 0; }
.mr-body { max-height: 60vh; min-height: 280px; overflow-y: auto; padding: var(--sp-3) 0 var(--sp-5); }
/* 固定信息区（不随列表滚动）：上端气口 + 底部分隔线 */
.mr-info-row { display: flex; align-items: baseline; justify-content: space-between; gap: var(--sp-4); padding: var(--sp-3) 0 var(--sp-4); margin: 0; border-bottom: 1px solid var(--c-border); }
.mr-hint { margin: 0; font-size: 13px; flex-shrink: 0; }
.mr-meta { margin: 0; font-size: 13px; color: var(--c-ink-2); }
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
.mr-footer { display: flex; align-items: center; justify-content: space-between; width: 100%; }
.mr-actions { display: flex; align-items: center; gap: var(--sp-2); }
.mr-count { font-size: 12px; }
</style>
