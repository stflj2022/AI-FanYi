import axios, { AxiosError } from 'axios'

// API 基础配置
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器（添加 JWT Token）
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器（处理错误）
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token 过期，跳转到登录页
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// 通用 API 方法（后端各端点直接返回 response_model，无 {data} 信封包装）
export const api = {
  get: <T>(url: string, params?: any): Promise<T> =>
    apiClient.get<T>(url, { params }).then((res) => res.data as T),

  post: <T>(url: string, data?: any): Promise<T> =>
    apiClient.post<T>(url, data).then((res) => res.data as T),

  put: <T>(url: string, data?: any): Promise<T> =>
    apiClient.put<T>(url, data).then((res) => res.data as T),

  delete: <T>(url: string): Promise<T> =>
    apiClient.delete<T>(url).then((res) => res.data as T),

  // 原始响应方法（直接返回完整响应）
  getRaw: <T>(url: string, params?: any) =>
    apiClient.get<T>(url, { params }).then((res) => res.data),

  postRaw: <T>(url: string, data?: any) =>
    apiClient.post<T>(url, data).then((res) => res.data),
}

export default apiClient
