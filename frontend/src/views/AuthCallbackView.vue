<template>
  <div class="callback">
    <div class="box">
      <el-icon v-if="!error" class="spin"><Loading /></el-icon>
      <p v-if="!error">正在完成登录…</p>
      <template v-else>
        <p class="err">登录失败：{{ error }}</p>
        <el-button @click="$router.replace({ name: 'login' })">返回登录</el-button>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const error = ref('')

onMounted(async () => {
  // 后端 OAuth 回调成功后重定向到此，携带 token（access_token / refresh_token）
  const access = route.query.access_token as string | undefined
  const refresh = route.query.refresh_token as string | undefined
  const redirect = (route.query.redirect as string) || '/board'

  if (access) {
    auth.setTokens(access, refresh)
    await auth.fetchCurrentUser()
    router.replace(redirect)
  } else {
    error.value = (route.query.error as string) || '未获取到登录凭证'
  }
})
</script>

<style scoped>
.callback {
  height: 100vh;
  display: grid;
  place-items: center;
  background: var(--c-canvas);
}
.box { text-align: center; color: var(--c-ink-2); }
.spin { font-size: 32px; color: var(--c-accent); animation: spin 1s linear infinite; }
.err { color: var(--c-status-overdue); margin-bottom: var(--sp-4); }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
