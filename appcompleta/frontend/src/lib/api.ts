import axios, { AxiosError } from 'axios'

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

api.interceptors.response.use(
  (response) => {
    return response
  },
  (error: AxiosError) => {
    if (error.response) {
      const status = error.response.status
      if (status === 401) {
        console.error('Unauthorized - redirect to login')
      } else if (status === 403) {
        console.error('Forbidden')
      } else if (status >= 500) {
        console.error('Server error:', error.response.data)
      }
    } else if (error.request) {
      console.error('Network error - no response received')
    }
    return Promise.reject(error)
  }
)

export const fetcher = async (url: string) => {
  const response = await api.get(url)
  return response.data
}

export default api
