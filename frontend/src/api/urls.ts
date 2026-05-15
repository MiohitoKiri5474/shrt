import { apiClient } from './client'

export interface URLOut {
  id: number
  short_code: string
  original_url: string
  created_at: string
  click_count: number
}

export interface StatsOut {
  url_id: number
  short_code: string
  original_url: string
  total_clicks: number
  clicks_by_date: Record<string, number>
}

export const urlsApi = {
  async create(original_url: string, custom_code?: string): Promise<URLOut> {
    const { data } = await apiClient.post<URLOut>('/api/urls', { original_url, custom_code })
    return data
  },
  async list(): Promise<URLOut[]> {
    const { data } = await apiClient.get<URLOut[]>('/api/urls')
    return data
  },
  async remove(id: number): Promise<void> {
    await apiClient.delete(`/api/urls/${id}`)
  },
  async stats(id: number): Promise<StatsOut> {
    const { data } = await apiClient.get<StatsOut>(`/api/urls/${id}/stats`)
    return data
  },
}
