import { defineStore } from 'pinia'
import { ref } from 'vue'
import { adminApi, type AdminUser } from '../api/admin'

export const useAdminStore = defineStore('admin', () => {
  const users = ref<AdminUser[]>([])

  async function fetchAll() {
    users.value = await adminApi.listUsers()
  }

  async function remove(id: number) {
    await adminApi.deleteUser(id)
    users.value = users.value.filter((u) => u.id !== id)
  }

  return { users, fetchAll, remove }
})
