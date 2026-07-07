import axios from 'axios'
import type { Router } from 'vue-router'

// In production, nginx proxies /api/* to the backend — no env var needed.
// Set VITE_API_BASE_URL to override (e.g. when backend is on a different host).
export const BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? ''

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
})

let _router: Router | null = null
export function setRouter(r: Router) {
  _router = r
}

// Endpoints where a 401 means "wrong current password", not "session expired" —
// the caller shows an inline error instead of being redirected to /login.
const AUTH_REDIRECT_EXEMPT_PATHS = ['/api/auth/me/email', '/api/auth/me/password']

apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    const url: string = error.config?.url ?? ''
    const isExempt = AUTH_REDIRECT_EXEMPT_PATHS.some((path) => url.includes(path))
    if (error.response?.status === 401 && !isExempt) {
      if (_router) {
        _router.push({ name: 'login' })
      } else {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)
