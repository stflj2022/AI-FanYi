import { useState, useEffect } from 'react'
import { Cpu, HardDrive, MemoryStick, Activity, Server, CheckCircle, XCircle, Clock } from 'lucide-react'

interface ResourceStatus {
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

interface WorkerStatus {
  id: string
  name: string
  status: string
  type: string
  jobs_completed: number
  jobs_failed: number
  current_job: string | null
  last_heartbeat: string | null
}

interface QueueStatus {
  pending: number
  running: number
  completed: number
  failed: number
  total: number
}

interface ModuleStatus {
  status: string
  name: string
}

interface SystemStatus {
  status: string
  uptime: number
  resources: ResourceStatus
  workers: WorkerStatus[]
  queue: QueueStatus
  modules: Record<string, ModuleStatus>
}

export function SystemStatusPage() {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadSystemStatus()
    const interval = setInterval(loadSystemStatus, 5000) // 每 5 秒刷新一次
    return () => clearInterval(interval)
  }, [])

  const loadSystemStatus = async () => {
    try {
      setError(null)
      const response = await fetch('/api/v1/system/status', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      })
      if (!response.ok) {
        throw new Error('无法获取系统状态')
      }
      const data = await response.json()
      setSystemStatus(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载系统状态失败')
    } finally {
      setLoading(false)
    }
  }

  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${days}天 ${hours}小时 ${minutes}分钟`
  }

  const formatBytes = (bytes: number): string => {
    if (bytes >= 1024 * 1024 * 1024) {
      return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
    } else if (bytes >= 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
    } else {
      return `${bytes} KB`
    }
  }

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'healthy':
      case 'ready':
      case 'idle':
        return 'text-green-600 bg-green-50'
      case 'running':
        return 'text-blue-600 bg-blue-50'
      case 'warning':
        return 'text-yellow-600 bg-yellow-50'
      case 'error':
      case 'failed':
        return 'text-red-600 bg-red-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
          <button
            onClick={loadSystemStatus}
            className="ml-4 underline hover:no-underline"
          >
            重试
          </button>
        </div>
      </div>
    )
  }

  if (!systemStatus) return null

  return (
    <div className="p-6">
      {/* 头部 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">系统状态</h1>
          <p className="text-gray-600 mt-1">监控系统资源和服务状态</p>
        </div>
        <div className="flex items-center space-x-2">
          <Activity className="w-5 h-5 text-green-600" />
          <span className="text-green-600 font-medium">运行中</span>
        </div>
      </div>

      {/* 运行时间 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
        <div className="flex items-center space-x-2 text-gray-600">
          <Clock className="w-5 h-5" />
          <span>系统运行时间：{formatUptime(systemStatus.uptime)}</span>
        </div>
      </div>

      {/* 系统资源 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        {/* CPU */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <Cpu className="w-5 h-5 text-indigo-600" />
              <span className="font-medium text-gray-900">CPU</span>
            </div>
            <span className="text-2xl font-bold text-gray-900">
              {systemStatus.resources.cpu_usage.toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-indigo-600 h-2 rounded-full transition-all"
              style={{ width: `${systemStatus.resources.cpu_usage}%` }}
            ></div>
          </div>
          <p className="text-sm text-gray-500 mt-2">
            {systemStatus.resources.cpu_cores} 核心
          </p>
        </div>

        {/* 内存 */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <MemoryStick className="w-5 h-5 text-purple-600" />
              <span className="font-medium text-gray-900">内存</span>
            </div>
            <span className="text-2xl font-bold text-gray-900">
              {systemStatus.resources.memory_usage.toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-purple-600 h-2 rounded-full transition-all"
              style={{ width: `${systemStatus.resources.memory_usage}%` }}
            ></div>
          </div>
          <p className="text-sm text-gray-500 mt-2">
            {systemStatus.resources.memory_used} / {systemStatus.resources.memory_total} MB
          </p>
        </div>

        {/* 磁盘 */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <HardDrive className="w-5 h-5 text-green-600" />
              <span className="font-medium text-gray-900">磁盘</span>
            </div>
            <span className="text-2xl font-bold text-gray-900">
              {systemStatus.resources.disk_usage.toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-green-600 h-2 rounded-full transition-all"
              style={{ width: `${systemStatus.resources.disk_usage}%` }}
            ></div>
          </div>
          <p className="text-sm text-gray-500 mt-2">
            {systemStatus.resources.disk_used} / {systemStatus.resources.disk_total} GB
          </p>
        </div>

        {/* GPU */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <Server className="w-5 h-5 text-blue-600" />
              <span className="font-medium text-gray-900">GPU</span>
            </div>
            {systemStatus.resources.gpu_usage !== null ? (
              <span className="text-2xl font-bold text-gray-900">
                {systemStatus.resources.gpu_usage.toFixed(1)}%
              </span>
            ) : (
              <span className="text-2xl font-bold text-gray-400">-</span>
            )}
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            {systemStatus.resources.gpu_usage !== null ? (
              <div
                className="bg-blue-600 h-2 rounded-full transition-all"
                style={{ width: `${systemStatus.resources.gpu_usage}%` }}
              ></div>
            ) : (
              <div className="bg-gray-400 h-2 rounded-full w-0"></div>
            )}
          </div>
          <p className="text-sm text-gray-500 mt-2">
            {systemStatus.resources.gpu_usage !== null
              ? `显存使用: ${systemStatus.resources.gpu_memory_usage?.toFixed(1)}%`
              : '未检测到 GPU'}
          </p>
        </div>
      </div>

      {/* Worker 状态 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Worker 状态</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead>
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">名称</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">状态</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">类型</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">已完成</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">失败</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">当前任务</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {systemStatus.workers.map((worker) => (
                <tr key={worker.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {worker.name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(worker.status)}`}>
                      {worker.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {worker.type}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {worker.jobs_completed}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {worker.jobs_failed}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {worker.current_job || '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 队列状态 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="text-sm text-gray-500 mb-1">待处理</div>
          <div className="text-3xl font-bold text-gray-900">{systemStatus.queue.pending}</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="text-sm text-gray-500 mb-1">运行中</div>
          <div className="text-3xl font-bold text-blue-600">{systemStatus.queue.running}</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="text-sm text-gray-500 mb-1">已完成</div>
          <div className="text-3xl font-bold text-green-600">{systemStatus.queue.completed}</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="text-sm text-gray-500 mb-1">失败</div>
          <div className="text-3xl font-bold text-red-600">{systemStatus.queue.failed}</div>
        </div>
      </div>

      {/* 模块状态 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Layer 0 模块状态</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Object.entries(systemStatus.modules).map(([id, module]) => (
            <div
              key={id}
              className="flex items-center justify-between p-3 border border-gray-200 rounded-lg"
            >
              <div>
                <div className="font-medium text-sm text-gray-900">{id}</div>
                <div className="text-xs text-gray-500">{module.name}</div>
              </div>
              <div className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(module.status)}`}>
                {module.status}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
