<template>
  <el-dialog
    :model-value="visible"
    title="开启周会 · 信息确认"
    width="440px"
    @update:model-value="(v: boolean) => emit('update:visible', v)"
  >
    <p class="mc-hint muted">请确认本次周会的信息，确认后开启周会记录模式。</p>
    <el-form label-width="80px" label-position="left">
      <el-form-item label="周会计次">
        <el-input-number v-model="form.session" :min="1" controls-position="right" style="width: 160px" />
        <span class="mc-tip muted">第 {{ form.session }} 次</span>
      </el-form-item>
      <el-form-item label="记录人">
        <el-input v-model="form.recorder" placeholder="记录人姓名" style="width: 220px" />
      </el-form-item>
      <el-form-item label="会议日期">
        <el-date-picker v-model="form.meeting_date" type="date" value-format="YYYY-MM-DD" style="width: 220px" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :loading="saving" @click="confirm">确认开启</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useMeetingStore } from '@/stores/meeting'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{
  visible: boolean
  defaultSession: number
}>()
const emit = defineEmits<{
  (e: 'update:visible', v: boolean): void
  (e: 'opened'): void
}>()

const meeting = useMeetingStore()
const auth = useAuthStore()
const saving = ref(false)

function todayStr(): string {
  const d = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

const form = reactive({
  session: props.defaultSession || 1,
  recorder: auth.currentUser?.name ?? '',
  meeting_date: todayStr(),
})

// 每次打开时用最新默认值重置
watch(() => props.visible, (v) => {
  if (v) {
    form.session = props.defaultSession || 1
    form.recorder = auth.currentUser?.name ?? ''
    form.meeting_date = todayStr()
  }
})

async function confirm() {
  if (!form.recorder.trim()) {
    ElMessage.warning('请填写记录人')
    return
  }
  saving.value = true
  try {
    await meeting.openMeeting({
      session: form.session,
      recorder: form.recorder.trim(),
      meeting_date: form.meeting_date,
    })
    ElMessage.success(`已开启第 ${form.session} 次周会记录`)
    emit('update:visible', false)
    emit('opened')
  } catch {
    ElMessage.error('开启失败（需要管理员权限）')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.mc-hint { font-size: 13px; margin: 0 0 var(--sp-3); }
.mc-tip { margin-left: var(--sp-3); font-size: 12px; }
</style>
