/**
 * CSRF Security Note
 * ------------------
 * CSRF is mitigated by the HttpOnly, SameSite=Strict cookie strategy.
 *
 * The backend sets `access_token` as an HttpOnly, SameSite=Strict cookie on login.
 * The frontend sends all requests with `withCredentials: true` (see client.ts).
 * Because the cookie is SameSite=Strict, the browser will not attach it to any
 * cross-origin request — a malicious page on another origin cannot trigger
 * authenticated state-changing requests.
 *
 * No Authorization header or localStorage token is used.
 *
 * See /SECURITY.md for a full discussion of the project's security posture.
 */
import { apiClient, BASE_URL } from './client'

export interface URLOut {
  id: number
  short_code: string
  original_url: string
  created_at: string
  click_count: number
  has_password: boolean
  expires_at: string | null
}

export interface URLUpdatePayload {
  short_code: string
  password?: string
  remove_password?: boolean
  expires_at?: string | null
}

export interface StatsOut {
  url_id: number
  short_code: string
  original_url: string
  total_clicks: number
  clicks_by_date: Record<string, number>
}

export const urlsApi = {
  async create(original_url: string, custom_code?: string, password?: string): Promise<URLOut> {
    const { data } = await apiClient.post<URLOut>('/api/urls', { original_url, custom_code, password })
    return data
  },
  async unlock(short_code: string, password: string): Promise<{ redirect_url: string }> {
    const { data } = await apiClient.post<{ redirect_url: string }>(`/api/urls/${short_code}/unlock`, { password })
    return data
  },
  async list(): Promise<URLOut[]> {
    const { data } = await apiClient.get<URLOut[]>('/api/urls')
    return data
  },
  async remove(id: number): Promise<void> {
    await apiClient.delete(`/api/urls/${id}`)
  },
  async update(id: number, payload: URLUpdatePayload): Promise<URLOut> {
    const { data } = await apiClient.patch<URLOut>(`/api/urls/${id}`, payload)
    return data
  },
  async stats(id: number): Promise<StatsOut> {
    const { data } = await apiClient.get<StatsOut>(`/api/urls/${id}/stats`)
    return data
  },
  /**
   * URL of the PNG QR code for a short link. Same-origin in the default
   * deployment, so the browser sends the auth cookie automatically when this is
   * used as an `<img>` src or a download anchor href.
   */
  qrUrl(shortCode: string): string {
    return `${BASE_URL}/api/urls/${encodeURIComponent(shortCode)}/qr`
  },
}
