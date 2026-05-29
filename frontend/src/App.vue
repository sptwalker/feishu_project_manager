<template>
  <div id="app">
    <el-container>
      <el-header>
        <h1>飞书项目管理系统</h1>
      </el-header>
      <el-main>
        <el-card>
          <template #header>
            <span>欢迎使用</span>
          </template>
          <p>系统正在初始化...</p>
          <el-button type="primary" @click="testApi">测试API连接</el-button>
          <p v-if="apiStatus">{{ apiStatus }}</p>
        </el-card>
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import axios from 'axios'

const apiStatus = ref('')

const testApi = async () => {
  try {
    const response = await axios.get('/api/v1/health')
    apiStatus.value = `API连接成功: ${JSON.stringify(response.data)}`
  } catch (error) {
    apiStatus.value = `API连接失败: ${error}`
  }
}
</script>

<style scoped>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.el-header {
  background-color: #3370ff;
  color: white;
  display: flex;
  align-items: center;
}

.el-header h1 {
  margin: 0;
  font-size: 20px;
}

.el-main {
  background-color: #f5f7fa;
  padding: 20px;
}
</style>
