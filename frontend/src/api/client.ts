import axios from 'axios'
import type { Router } from 'vue-router'

export const BASE_URL: string = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

let _router: Router | null = null
export function setRouter(r: Router) {
  _router = r
}

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      if (_router) {
        _router.push({ name: 'login', query: { redirect: _router.currentRoute.value.fullPath } })
      } else {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)
