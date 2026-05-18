import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type UserOut } from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserOut | null>(null)
  const isAuthenticated = computed(() => user.value !== null)

  async function login(email: string, password: string) {
    await authApi.login(email, password)
    user.value = await authApi.me()
  }

  function logout() {
    user.value = null
  }

  async function restore() {
    try {
      user.value = await authApi.me()
    } catch {
      logout()
    }
  }

  return { user, isAuthenticated, login, logout, restore }
})
