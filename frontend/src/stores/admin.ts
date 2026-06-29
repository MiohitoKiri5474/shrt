import { defineStore } from 'pinia'
import { ref } from 'vue'
import { adminApi, type AdminUser } from '../api/admin'

export const useAdminStore = defineStore('admin', () => {
  const users = ref<AdminUser[]>([])

  async function fetchAll() {
    users.value = await adminApi.listUsers()
  }

  async function toggleRole(id: number, is_admin: boolean) {
    const updated = await adminApi.updateUser(id, is_admin)
    users.value = users.value.map((u) => (u.id === id ? { ...u, ...updated } : u))
  }

  async function remove(id: number) {
    await adminApi.deleteUser(id)
    users.value = users.value.filter((u) => u.id !== id)
  }

  return { users, fetchAll, toggleRole, remove }
})
