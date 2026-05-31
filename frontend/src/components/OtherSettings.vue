<template>
  <div class="other-settings" v-loading="loading">
    <section class="card">
      <h3 class="card-title">周例会次数设置</h3>

      <template v-if="state">
        <!-- 本周已召开 -->
        <div v-if="state.this_week_recorded" class="info-block">
          <div class="info-row">
            <span class="ilabel">本周状态</span>
            <span class="ival ok">本周已召开第 {{ state.this_week_count }} 次周例会</span>
          </div>
          <div class="info-row">
            <span class="ilabel">下一次周例会</span>
            <span class="ival">{{ state.calibration_monday }}（周一）· 应为第 <b>{{ state.calibration_count }}</b> 次</span>
          </div>
        </div>

        <!-- 本周未召开 -->
        <div v-else class="info-block">
          <div class="info-row">
            <span class="ilabel">上一次周例会</span>
            <span class="ival">
              <template v-if="state.last_meeting">{{ state.last_meeting.date }} · 第 {{ state.last_meeting.count }} 次</template>
              <span v-else class="muted">暂无记录</span>
            </span>
          </div>
          <div class="info-row">
            <span class="ilabel">本周周例会</span>
            <span class="ival">{{ state.this_week_monday }}（周一）· 将为第 <b>{{ state.calibration_count }}</b> 次</span>
          </div>
        </div>

        <!-- 校准 -->
        <div class="calibrate">
          <span class="ilabel">校准次数</span>
          <el-input-number
            v-model="editCount" :min="1" :disabled="!isAdmin" controls-position="right" style="width: 140px"
          />
          <el-button type="primary" :loading="saving" :disabled="!isAdmin || editCount === state.calibration_count" @click="save">
            保存
          </el-button>
          <span v-if="!isAdmin" class="muted hint">（仅管理员可修改）</span>
        </div>
        <p class="tip muted">
          说明：周会次数按自然周递增——同一周内次数不变，跨到新的一周自动 +1。
          修改"校准次数"将把 {{ state.calibration_monday }} 那一周设为该次数，并以此为基准向后推算。
        </p>
      </template>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useMeetingStore } from '@/stores/meeting'
import { useAuthStore } from '@/stores/auth'

const meeting = useMeetingStore()
const auth = useAuthStore()

const loading = ref(false)
const saving = ref(false)
const editCount = ref(0)

const state = computed(() => meeting.state)
const isAdmin = computed(() => auth.currentUser?.role === 'admin')

async function load() {
  loading.value = true
  try {
    await meeting.load()
    editCount.value = meeting.state?.calibration_count ?? 0
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    await meeting.setCount(editCount.value)
    editCount.value = meeting.state?.calibration_count ?? editCount.value
    ElMessage.success('周会次数已校准')
  } catch {
    ElMessage.error('保存失败（需要管理员权限）')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.other-settings { padding: var(--sp-2) 0; }
.card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  padding: var(--sp-5);
  max-width: 640px;
  box-shadow: var(--shadow-sm);
}
.card-title { font-size: 15px; margin-bottom: var(--sp-4); }

.info-block { display: flex; flex-direction: column; gap: var(--sp-3); margin-bottom: var(--sp-4); }
.info-row { display: flex; align-items: center; gap: var(--sp-3); }
.ilabel { width: 96px; flex-shrink: 0; color: var(--c-ink-3); font-size: 13px; }
.ival { color: var(--c-ink); font-weight: 500; }
.ival.ok { color: #1a73e8; font-weight: 600; }

.calibrate { display: flex; align-items: center; gap: var(--sp-3); padding-top: var(--sp-3); border-top: 1px solid var(--c-border); }
.hint { font-size: 12px; }
.tip { margin: var(--sp-3) 0 0; font-size: 12px; line-height: 1.6; }
</style>
