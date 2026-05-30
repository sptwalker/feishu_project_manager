import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { tokenStore } from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(tokenStore.access)

  const isAuthenticated = computed(() => !!accessToken.value)

  function setTokens(access: string, refresh?: string) {
    tokenStore.set(access, refresh)
    accessToken.value = access
  }

  function logout() {
    tokenStore.clear()
    accessToken.value = null
  }

  return { accessToken, isAuthenticated, setTokens, logout }
})
