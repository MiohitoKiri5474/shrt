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
}
