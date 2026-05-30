import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { tokenStore } from '@/api/client'
import { userApi } from '@/api/resources'
import type { User } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(tokenStore.access)
  const currentUser = ref<User | null>(null)

  const isAuthenticated = computed(() => !!accessToken.value)

  function setTokens(access: string, refresh?: string) {
    tokenStore.set(access, refresh)
    accessToken.value = access
  }

  async function fetchCurrentUser() {
    if (!accessToken.value) return null
    try {
      currentUser.value = await userApi.me()
    } catch {
      currentUser.value = null
    }
    return currentUser.value
  }

  function logout() {
    tokenStore.clear()
    accessToken.value = null
    currentUser.value = null
  }

  return { accessToken, currentUser, isAuthenticated, setTokens, fetchCurrentUser, logout }
})
