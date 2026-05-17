import axios from 'axios'

const _baseURL = import.meta.env.VITE_API_BASE_URL
if (!_baseURL && import.meta.env.PROD) {
  throw new Error('VITE_API_BASE_URL is required in production')
}
export const BASE_URL: string = _baseURL || 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
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
