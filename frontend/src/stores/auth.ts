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

  async function logout() {
    try {
      await authApi.logout()
    } finally {
      // Always clear local state even if the backend call fails,
      // so the UI never shows a stale authenticated session.
      user.value = null
    }
  }

  async function restore() {
    try {
      user.value = await authApi.me()
    } catch {
      // Do not call logout() here — that would POST to /api/auth/logout and
      // invalidate a valid session cookie (e.g. on page reload while logged in).
      // Just clear local state so the guard redirects to /login.
      user.value = null
    }
  }

  async function updateUsername(username: string) {
    user.value = await authApi.updateUsername(username)
  }

  async function updateEmail(currentPassword: string, newEmail: string) {
    user.value = await authApi.updateEmail(currentPassword, newEmail)
  }

  async function updatePassword(currentPassword: string, newPassword: string) {
    await authApi.updatePassword(currentPassword, newPassword)
  }

  return { user, isAuthenticated, login, logout, restore, updateUsername, updateEmail, updatePassword }
})
