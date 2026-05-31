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

apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      if (_router) {
        _router.push({ name: 'login', query: { redirect: _router.currentRoute.value.fullPath } })
      } else {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)
