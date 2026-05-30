<template>
  <div class="ptabs">
    <RouterLink :to="{ name: 'project-tasks', params: { id: projectId } }" class="ptab" active-class="active">
      任务
    </RouterLink>
    <RouterLink :to="{ name: 'project-risks', params: { id: projectId } }" class="ptab" active-class="active">
      风险
    </RouterLink>
  </div>
</template>

<script setup lang="ts">
defineProps<{ projectId: number | string }>()
</script>

<style scoped>
.ptabs {
  display: inline-flex;
  gap: 2px;
  background: var(--c-surface-2);
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  padding: 3px;
}
.ptab {
  padding: 6px 18px;
  border-radius: var(--r-sm);
  font-weight: 600;
  font-size: 13px;
  color: var(--c-ink-3);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.ptab:hover { color: var(--c-ink); }
.ptab.active {
  background: var(--c-surface);
  color: var(--c-accent);
  box-shadow: var(--shadow-sm);
}
</style>
