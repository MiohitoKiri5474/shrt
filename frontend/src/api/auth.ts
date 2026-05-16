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

export interface UserOut {
  id: number
  email: string
  created_at: string
}

export interface Token {
  access_token: string
  token_type: string
}

export const authApi = {
  async register(email: string, password: string): Promise<UserOut> {
    const { data } = await apiClient.post<UserOut>('/api/auth/register', { email, password })
    return data
  },
  async login(email: string, password: string): Promise<Token> {
    const form = new URLSearchParams({ username: email, password })
    const { data } = await apiClient.post<Token>('/api/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    return data
  },
  async me(): Promise<UserOut> {
    const { data } = await apiClient.get<UserOut>('/api/auth/me')
    return data
  },
  async addUser(email: string, password: string): Promise<UserOut> {
    const { data } = await apiClient.post<UserOut>('/api/auth/users', { email, password })
    return data
  },
}
