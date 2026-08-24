import type { Project } from '../../types'
import { Edit, Trash2, FolderOpen } from 'lucide-react'

interface ProjectCardProps {
  project: Project
  onEdit: (project: Project) => void
  onDelete: (projectId: string) => void
  onView: (projectId: string) => void
}

export function ProjectCard({ project, onEdit, onDelete, onView }: ProjectCardProps) {
  const statusColors = {
    created: 'bg-gray-100 text-gray-700',
    in_progress: 'bg-blue-100 text-blue-700',
    completed: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700',
    archived: 'bg-yellow-100 text-yellow-700',
  }

  const statusLabels = {
    created: '已创建',
    in_progress: '进行中',
    completed: '已完成',
    failed: '失败',
    archived: '已归档',
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
      {/* 头部 */}
      <div className="flex items-start justify-between mb-4">
        <div
          className="flex items-center justify-center w-12 h-12 rounded-lg bg-indigo-50 text-indigo-600 cursor-pointer"
          onClick={() => onView(project.id)}
        >
          <FolderOpen size={24} />
        </div>
        <span
          className={`px-3 py-1 rounded-full text-xs font-medium ${
            statusColors[project.status as keyof typeof statusColors] || statusColors.created
          }`}
        >
          {statusLabels[project.status as keyof typeof statusLabels] || project.status}
        </span>
      </div>

      {/* 内容 */}
      <h3
        className="text-lg font-semibold text-gray-900 mb-2 cursor-pointer hover:text-indigo-600"
        onClick={() => onView(project.id)}
      >
        {project.name}
      </h3>
      {project.description && (
        <p className="text-sm text-gray-600 mb-3 line-clamp-2">{project.description}</p>
      )}

      {/* 影视信息 */}
      {project.title && (
        <div className="text-sm text-gray-500 mb-3">
          {project.title}
          {project.season && <span className="ml-2">S{project.season}</span>}
          {project.episode && <span className="ml-1">E{project.episode}</span>}
        </div>
      )}

      {/* 底部信息 */}
      <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-100">
        <span className="text-xs text-gray-400">
          {new Date(project.created_at).toLocaleDateString('zh-CN')}
        </span>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => onEdit(project)}
            className="p-2 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
            title="编辑"
          >
            <Edit size={16} />
          </button>
          <button
            onClick={() => onDelete(project.id)}
            className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            title="删除"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}
