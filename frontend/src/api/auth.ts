/**
 * CSRF Security Note
 * ------------------
 * Authentication tokens are stored in HttpOnly cookies set by the backend.
 * The browser sends these cookies automatically on same-origin requests.
 *
 * CSRF mitigation relies on the SameSite=Lax (or Strict) cookie attribute
 * set by the server. Cross-origin non-safe requests (POST, PUT, DELETE) that
 * would carry SameSite=Lax cookies are blocked by modern browsers, preventing
 * CSRF for state-changing endpoints.
 *
 * See /SECURITY.md for a broader discussion of the project's security posture.
 */
import { apiClient } from './client'

export interface UserOut {
  email: string
  created_at: string
}

export interface Token {
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
  async logout(): Promise<void> {
    await apiClient.post('/api/auth/logout')
  },
}
