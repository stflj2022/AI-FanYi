import { JobResponse } from '../../services/jobAPI'
import { Link } from 'react-router-dom'

interface RecentJobsListProps {
  jobs: JobResponse[]
  loading?: boolean
}

interface StatusBadgeProps {
  status: JobResponse['status']
}

function StatusBadge({ status }: StatusBadgeProps) {
  const statusConfig = {
    pending: { label: '等待中', color: 'bg-gray-100 text-gray-800' },
    scheduled: { label: '已调度', color: 'bg-blue-100 text-blue-800' },
    running: { label: '运行中', color: 'bg-green-100 text-green-800' },
    waiting: { label: '已暂停', color: 'bg-yellow-100 text-yellow-800' },
    completed: { label: '已完成', color: 'bg-green-100 text-green-800' },
    failed: { label: '失败', color: 'bg-red-100 text-red-800' },
    cancelled: { label: '已取消', color: 'bg-gray-100 text-gray-800' },
    retrying: { label: '重试中', color: 'bg-orange-100 text-orange-800' },
  }

  const config = statusConfig[status] || statusConfig.pending

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${config.color}`}>
      {config.label}
    </span>
  )
}

export function RecentJobsList({ jobs, loading }: RecentJobsListProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold">最近任务</h2>
        </div>
        <div className="p-6">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="flex items-center justify-between py-4 border-b border-gray-100 last:border-0 animate-pulse"
            >
              <div className="flex-1">
                <div className="h-4 bg-gray-200 rounded w-1/3 mb-2"></div>
                <div className="h-3 bg-gray-200 rounded w-1/4"></div>
              </div>
              <div className="h-6 bg-gray-200 rounded w-20"></div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (jobs.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold">最近任务</h2>
        </div>
        <div className="p-12 text-center">
          <div className="text-6xl mb-4">📋</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">暂无任务</h3>
          <p className="text-gray-500 mb-6">
            还没有创建任何配音任务，点击上方按钮开始吧！
          </p>
          <Link
            to="/upload"
            className="inline-block px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            上传视频
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <h2 className="text-lg font-semibold">最近任务</h2>
        <Link
          to="/jobs"
          className="text-sm text-blue-600 hover:text-blue-700"
        >
          查看全部 →
        </Link>
      </div>
      <div className="divide-y divide-gray-100">
        {jobs.map((job) => (
          <Link
            key={job.id}
            to={`/jobs/${job.id}`}
            className="block px-6 py-4 hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3">
                  <h3 className="text-sm font-medium text-gray-900 truncate">
                    {job.name}
                  </h3>
                  <StatusBadge status={job.status} />
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {job.description || '无描述'}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  创建于 {new Date(job.created_at).toLocaleString('zh-CN')}
                </p>
              </div>
              <div className="flex items-center gap-4 text-xs text-gray-500 ml-4">
                {job.started_at && (
                  <span>
                    {new Date(job.started_at).toLocaleString('zh-CN')}
                  </span>
                )}
                <svg
                  className="w-4 h-4 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
