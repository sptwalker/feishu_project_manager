<template>
  <el-drawer
    :model-value="visible"
    size="62%"
    :with-header="false"
    @update:model-value="onDrawerToggle"
  >
    <ProjectDetailContent
      ref="contentRef"
      :visible="visible"
      :project="project"
      :departments="departments"
      :owners="owners"
      :create-mode="createMode"
      @updated="emit('updated')"
      @request-close="requestClose"
    />
  </el-drawer>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ProjectDetailContent from './ProjectDetailContent.vue'
import type { Project } from '@/types'

/* 对外契约：与重构前完全一致的 5 props + 2 emit。
   壳只负责 el-drawer 的开关；内容主体与全部编辑逻辑在 ProjectDetailContent。 */
defineProps<{
  visible: boolean
  project: Project | null
  departments?: string[]
  owners?: string[]
  createMode?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:visible', v: boolean): void
  (e: 'updated'): void
}>()

const contentRef = ref<InstanceType<typeof ProjectDetailContent> | null>(null)

/* el-drawer 自身触发的开关（点遮罩/ESC）：关闭时先让 content 做未来时间校验 + 提交进展 */
function onDrawerToggle(next: boolean) {
  if (!next) {
    requestClose()
  } else {
    emit('update:visible', true)
  }
}

/* content 主动请求关闭，或 drawer 关闭：统一走 content 的关闭前校验。
   flushBeforeClose 返回 false（有未来时间）时阻止关闭。 */
function requestClose() {
  const ok = contentRef.value?.flushBeforeClose() ?? true
  if (ok) emit('update:visible', false)
}
</script>
