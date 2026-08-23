import { api } from './api'

/** 系统资源状态 */
export interface SystemResourceStatus {
  cpu_usage: number
  cpu_cores: number
  memory_usage: number
  memory_total: number
  memory_used: number
  disk_usage: number
  disk_total: number
  disk_used: number
  gpu_usage: number | null
  gpu_memory_usage: number | null
}

/** Worker 状态 */
export interface WorkerStatus {
  id: string
  name: string
  status: string
  type: string
  jobs_completed: number
  jobs_failed: number
  current_job: string | null
  last_heartbeat: string | null
}

/** 队列状态 */
export interface QueueStatus {
  pending: number
  running: number
  completed: number
  failed: number
  total: number
}

/** 系统状态 */
export interface SystemStatus {
  status: string
  uptime: number
  resources: SystemResourceStatus
  workers: WorkerStatus[]
  queue: QueueStatus
  modules: Record<string, { status: string; name: string }>
}

/** 系统 API */
export const systemAPI = {
  /** 获取系统状态 */
  getStatus: async (): Promise<SystemStatus> => {
    const response = await api.get<SystemStatus>('/system/status')
    return response
  },

  /** 获取 Worker 状态 */
  getWorkers: async (): Promise<WorkerStatus[]> => {
    const response = await api.get<WorkerStatus[]>('/system/workers')
    return response
  },

  /** 获取队列状态 */
  getQueue: async (): Promise<QueueStatus> => {
    const response = await api.get<QueueStatus>('/system/queue')
    return response
  },
}
