import { apiClient } from './client'

export interface AdminUser {
  id: number
  email: string
  username: string | null
  is_admin: boolean
  created_at: string
  url_count: number
}

export const adminApi = {
  async listUsers(): Promise<AdminUser[]> {
    const { data } = await apiClient.get<AdminUser[]>('/api/admin/users')
    return data
  },
  async deleteUser(id: number): Promise<void> {
    await apiClient.delete(`/api/admin/users/${id}`)
  },
}
