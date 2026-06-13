<template>
  <div class="page">
    <div class="page-head">
      <h1 class="page-title">系统设置</h1>
    </div>

    <el-tabs v-model="activeTab" class="settings-tabs">
      <el-tab-pane label="用户管理" name="users">
        <UserManagement />
      </el-tab-pane>
      <el-tab-pane label="部门管理" name="departments">
        <DepartmentManagement />
      </el-tab-pane>
      <el-tab-pane label="周会设置" name="meeting">
        <MeetingSettings />
      </el-tab-pane>
      <el-tab-pane label="催办设置" name="followup">
        <FollowupSettings />
      </el-tab-pane>
      <el-tab-pane label="AI API设置" name="ai">
        <div class="empty-tab">
          <el-empty description="AI API设置功能开发中" />
        </div>
      </el-tab-pane>
      <el-tab-pane label="页面主题" name="theme">
        <div class="empty-tab">
          <el-empty description="页面主题设置功能开发中" />
        </div>
      </el-tab-pane>
      <el-tab-pane label="其他设置" name="other">
        <OtherSettings />
      </el-tab-pane>
      <el-tab-pane label="系统日志" name="logs">
        <SystemLog />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import UserManagement from '@/components/UserManagement.vue'
import DepartmentManagement from '@/components/DepartmentManagement.vue'
import MeetingSettings from '@/components/MeetingSettings.vue'
import FollowupSettings from '@/components/FollowupSettings.vue'
import OtherSettings from '@/components/OtherSettings.vue'
import SystemLog from '@/components/SystemLog.vue'

const activeTab = ref('users')
</script>

<style scoped>
.settings-tabs {
  margin-top: var(--sp-4);
}

.empty-tab {
  padding: var(--sp-8) 0;
  display: flex;
  justify-content: center;
  align-items: center;
}

:deep(.el-tabs__nav-wrap::after) {
  background-color: var(--c-border);
}

:deep(.el-tabs__item) {
  font-size: 15px;
  font-weight: 500;
}

:deep(.el-tabs__item.is-active) {
  color: var(--c-accent);
}
</style>
