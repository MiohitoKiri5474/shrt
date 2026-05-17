/**
 * CSRF Security Note
 * ------------------
 * CSRF attacks are currently mitigated by this module's use of the Authorization
 * header to carry Bearer tokens (set by the Axios request interceptor in client.ts).
 *
 * Why this works: the browser's Same-Origin Policy prevents cross-origin pages from
 * setting custom request headers such as `Authorization`. A malicious third-party site
 * therefore cannot craft a request that includes a valid Bearer token, so every
 * authenticated request arriving at the backend must have originated from JavaScript
 * running on the same origin as the frontend.
 *
 * IMPORTANT — Migration warning: this CSRF mitigation is tightly coupled to the current
 * token-storage strategy of keeping the access token in localStorage and sending it via
 * the Authorization header. If token storage is ever migrated to HttpOnly cookies (which
 * the browser sends automatically, including cross-origin), the Authorization-header
 * defense no longer applies and explicit CSRF protection (e.g., a CSRF token in a
 * custom header, or the SameSite=Strict/Lax cookie attribute) MUST be implemented
 * before or at the same time as that migration.
 *
 * See /SECURITY.md for a broader discussion of the project's security posture.
 */
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
