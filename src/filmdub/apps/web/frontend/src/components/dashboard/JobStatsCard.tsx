import type { JobStatsResponse } from '../../services/jobAPI'

interface JobStatsCardProps {
  stats: JobStatsResponse
  loading?: boolean
}

export function JobStatsCard({ stats, loading }: JobStatsCardProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="p-6 bg-white rounded-lg border border-gray-200 animate-pulse">
            <div className="h-4 bg-gray-200 rounded mb-2 w-1/2"></div>
            <div className="h-8 bg-gray-200 rounded w-1/3"></div>
          </div>
        ))}
      </div>
    )
  }

  const statItems = [
    { label: '总任务', value: stats.total, color: 'text-gray-900', bgColor: 'bg-gray-50' },
    {
      label: '运行中',
      value: stats.active,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      label: '已完成',
      value: stats.completed,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      label: '失败',
      value: stats.failed,
      color: 'text-red-600',
      bgColor: 'bg-red-50',
    },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      {statItems.map((item) => (
        <div
          key={item.label}
          className={`p-6 rounded-lg border border-gray-200 ${item.bgColor}`}
        >
          <p className={`text-sm font-medium ${item.color} mb-1`}>{item.label}</p>
          <p className={`text-3xl font-bold ${item.color}`}>{item.value}</p>
        </div>
      ))}
    </div>
  )
}
