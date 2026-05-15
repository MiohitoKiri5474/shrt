import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type UserOut } from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserOut | null>(null)
  const isAuthenticated = computed(() => user.value !== null)

  async function login(email: string, password: string) {
    const token = await authApi.login(email, password)
    localStorage.setItem('access_token', token.access_token)
    user.value = await authApi.me()
  }

  function logout() {
    localStorage.removeItem('access_token')
    user.value = null
  }

  async function restore() {
    const token = localStorage.getItem('access_token')
    if (!token) return
    try {
      user.value = await authApi.me()
    } catch {
      logout()
    }
  }

  return { user, isAuthenticated, login, logout, restore }
})
