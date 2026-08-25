import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Search } from 'lucide-react'
import { useProjectStore } from '../store/projectStore'
import { ProjectCard } from '../components/project/ProjectCard'
import type { Project } from '../types'

export function ProjectList() {
  const {
    projects,
    total,
    page,
    page_size,
    isLoading,
    error,
    fetchProjects,
    deleteProject,
    clearError,
  } = useProjectStore()

  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  useEffect(() => {
    fetchProjects({ search: searchQuery, status: statusFilter || undefined })
  }, [searchQuery, statusFilter])

  const handleDelete = async (projectId: string) => {
    if (confirm('确定要删除这个项目吗？')) {
      try {
        await deleteProject(projectId)
      } catch (error) {
        console.error('删除项目失败:', error)
      }
    }
  }

  const handleEdit = (project: Project) => {
    // TODO: 打开编辑对话框
    console.log('编辑项目:', project.id)
  }

  const handleView = (projectId: string) => {
    // TODO: 跳转到项目详情页
    console.log('查看项目:', projectId)
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    fetchProjects({ search: searchQuery, status: statusFilter || undefined })
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
          <button
            onClick={clearError}
            className="ml-4 underline hover:no-underline"
          >
            重试
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      {/* 头部 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">项目列表</h1>
          <p className="text-gray-600 mt-1">管理您的配音项目</p>
        </div>
        <Link
          to="/projects/new"
          className="flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
        >
          <Plus size={20} className="mr-2" />
          新建项目
        </Link>
      </div>

      {/* 搜索和筛选 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
        <form onSubmit={handleSearch} className="flex items-center space-x-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              placeholder="搜索项目名称、标题或描述..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">所有状态</option>
            <option value="pending">待处理</option>
            <option value="intake">录入中</option>
            <option value="in_progress">进行中</option>
            <option value="processing">处理中</option>
            <option value="review">待审核</option>
            <option value="completed">已完成</option>
            <option value="failed">失败</option>
            <option value="archived">已归档</option>
          </select>
          <button
            type="submit"
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            搜索
          </button>
        </form>
      </div>

      {/* 项目列表 */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        </div>
      ) : projects.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500">暂无项目</p>
          <Link
            to="/projects/new"
            className="inline-flex items-center mt-4 text-indigo-600 hover:text-indigo-700"
          >
            <Plus size={20} className="mr-2" />
            创建第一个项目
          </Link>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onEdit={handleEdit}
                onDelete={handleDelete}
                onView={handleView}
              />
            ))}
          </div>

          {/* 分页 */}
          <div className="flex items-center justify-between mt-8">
            <span className="text-sm text-gray-600">
              共 {total} 个项目
            </span>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => fetchProjects({ page: page - 1 })}
                disabled={page === 1}
                className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                上一页
              </button>
              <span className="px-4 py-2">
                第 {page} 页
              </span>
              <button
                onClick={() => fetchProjects({ page: page + 1 })}
                disabled={page * page_size >= total}
                className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                下一页
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
