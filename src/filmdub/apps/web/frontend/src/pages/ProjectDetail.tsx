import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { projectAPI } from '../services/projectAPI'

const statusColors: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
  intake: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  processing: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  review: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  completed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  archived: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
}

const statusLabels: Record<string, string> = {
  pending: '待处理',
  intake: '媒体摄入',
  processing: '处理中',
  review: '审核中',
  completed: '已完成',
  failed: '失败',
  archived: '已归档',
}

export function ProjectDetail() {
  const { id } = useParams<{ id: string }>()

  const { data: project, isLoading, error } = useQuery({
    queryKey: ['project', id],
    queryFn: () => projectAPI.get(id!),
  })

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  if (error || !project) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-medium text-gray-900 dark:text-white mb-2">
            加载项目失败
          </h2>
          <Link
            to="/projects"
            className="text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300"
          >
            返回项目列表
          </Link>
        </div>
      </div>
    )
  }

  const statusColor = statusColors[project.status] || statusColors.pending
  const statusLabel = statusLabels[project.status] || project.status

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between mb-4">
            <Link
              to="/projects"
              className="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
            >
              ← 返回项目列表
            </Link>
            <div className="flex gap-2">
              <Link
                to={`/projects/${project.id}/edit`}
                className="inline-flex items-center px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-md text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                编辑
              </Link>
            </div>
          </div>

          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                {project.name}
              </h1>
              {project.title && (
                <p className="text-lg text-gray-600 dark:text-gray-300">
                  {project.title}
                  {project.title_en && ` / ${project.title_en}`}
                </p>
              )}
            </div>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusColor}`}>
              {statusLabel}
            </span>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Info */}
          <div className="lg:col-span-2 space-y-6">
            {/* Description */}
            {project.description && (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  项目描述
                </h2>
                <p className="text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
                  {project.description}
                </p>
              </div>
            )}

            {/* Media Info */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                影片信息
              </h2>
              <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {project.media_type && (
                  <>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">媒体类型</dt>
                    <dd className="text-sm text-gray-900 dark:text-white">{project.media_type}</dd>
                  </>
                )}
                {project.season && project.episode && (
                  <>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">季/集</dt>
                    <dd className="text-sm text-gray-900 dark:text-white">
                      第 {project.season} 季 第 {project.episode} 集
                    </dd>
                  </>
                )}
                {project.year && (
                  <>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">年份</dt>
                    <dd className="text-sm text-gray-900 dark:text-white">{project.year}</dd>
                  </>
                )}
                {project.original_language && (
                  <>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">原始语言</dt>
                    <dd className="text-sm text-gray-900 dark:text-white">{project.original_language}</dd>
                  </>
                )}
                <>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">目标语言</dt>
                  <dd className="text-sm text-gray-900 dark:text-white">{project.target_language}</dd>
                </>
              </dl>
            </div>

            {/* External IDs */}
            {(project.tmdb_id || project.imdb_id) && (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  外部数据源
                </h2>
                <dl className="space-y-2">
                  {project.tmdb_id && (
                    <>
                      <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">TMDB ID</dt>
                      <dd className="text-sm text-gray-900 dark:text-white">{project.tmdb_id}</dd>
                    </>
                  )}
                  {project.imdb_id && (
                    <>
                      <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">IMDB ID</dt>
                      <dd className="text-sm text-gray-900 dark:text-white">{project.imdb_id}</dd>
                    </>
                  )}
                </dl>
              </div>
            )}

            {/* Config */}
            {project.config && Object.keys(project.config).length > 0 && (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  项目配置
                </h2>
                <pre className="text-sm text-gray-600 dark:text-gray-300 overflow-x-auto bg-gray-50 dark:bg-gray-900 p-4 rounded-md">
                  {JSON.stringify(project.config, null, 2)}
                </pre>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Time Info */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                时间信息
              </h2>
              <dl className="space-y-3">
                <div>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">创建时间</dt>
                  <dd className="text-sm text-gray-900 dark:text-white mt-1">
                    {new Date(project.created_at).toLocaleString('zh-CN')}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">更新时间</dt>
                  <dd className="text-sm text-gray-900 dark:text-white mt-1">
                    {new Date(project.updated_at).toLocaleString('zh-CN')}
                  </dd>
                </div>
                {project.started_at && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">开始时间</dt>
                    <dd className="text-sm text-gray-900 dark:text-white mt-1">
                      {new Date(project.started_at).toLocaleString('zh-CN')}
                    </dd>
                  </div>
                )}
                {project.completed_at && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">完成时间</dt>
                    <dd className="text-sm text-gray-900 dark:text-white mt-1">
                      {new Date(project.completed_at).toLocaleString('zh-CN')}
                    </dd>
                  </div>
                )}
              </dl>
            </div>

            {/* Actions */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                快速操作
              </h2>
              <div className="space-y-3">
                <Link
                  to={`/projects/${project.id}/upload`}
                  className="block w-full text-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
                >
                  上传视频
                </Link>
                <Link
                  to={`/projects/${project.id}/jobs`}
                  className="block w-full text-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  查看任务
                </Link>
                <Link
                  to={`/projects/${project.id}/characters`}
                  className="block w-full text-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  管理人物
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
