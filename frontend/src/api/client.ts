import axios from 'axios'

const baseURL: string = import.meta.env.VITE_API_BASE_URL
  ?? (import.meta.env.PROD
    ? (() => { throw new Error('VITE_API_BASE_URL must be set in production builds') })()
    : 'http://localhost:8000')

export const apiClient = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
})

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
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)
