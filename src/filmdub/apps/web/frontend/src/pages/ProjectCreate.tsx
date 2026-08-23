import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { useProjectStore } from '../store/projectStore'
import type { ProjectCreate } from '../types'

export function ProjectCreate() {
  const navigate = useNavigate()
  const { createProject, isCreating, error, clearError } = useProjectStore()

  const [formData, setFormData] = useState<ProjectCreate>({
    name: '',
    description: '',
    target_language: 'zh',
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.name.trim()) {
      alert('项目名称不能为空')
      return
    }

    try {
      const project = await createProject(formData)
      navigate(`/projects/${project.id}`)
    } catch (err) {
      // 错误已在 store 中处理
    }
  }

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
    if (error) clearError()
  }

  return (
    <div className="p-6">
      {/* 头部 */}
      <div className="mb-6">
        <Link
          to="/projects"
          className="inline-flex items-center text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft size={20} className="mr-2" />
          返回项目列表
        </Link>
        <h1 className="text-2xl font-bold text-gray-900">创建新项目</h1>
        <p className="text-gray-600 mt-1">填写项目信息</p>
      </div>

      {/* 表单 */}
      <div className="max-w-2xl">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          {/* 基本信息 */}
          <div className="space-y-4">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                项目名称 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="name"
                name="name"
                required
                value={formData.name}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="例如：老友记 第一季"
              />
            </div>

            <div>
              <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
                项目描述
              </label>
              <textarea
                id="description"
                name="description"
                rows={3}
                value={formData.description || ''}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="简要描述项目内容..."
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-2">
                  影视标题
                </label>
                <input
                  type="text"
                  id="title"
                  name="title"
                  value={formData.title || ''}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="原标题"
                />
              </div>

              <div>
                <label htmlFor="title_en" className="block text-sm font-medium text-gray-700 mb-2">
                  英文标题
                </label>
                <input
                  type="text"
                  id="title_en"
                  name="title_en"
                  value={formData.title_en || ''}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="English Title"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="season" className="block text-sm font-medium text-gray-700 mb-2">
                  季数
                </label>
                <input
                  type="number"
                  id="season"
                  name="season"
                  min={1}
                  value={formData.season || ''}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="1"
                />
              </div>

              <div>
                <label htmlFor="episode" className="block text-sm font-medium text-gray-700 mb-2">
                  集数
                </label>
                <input
                  type="number"
                  id="episode"
                  name="episode"
                  min={1}
                  value={formData.episode || ''}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="1"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="original_language" className="block text-sm font-medium text-gray-700 mb-2">
                  原始语言
                </label>
                <select
                  id="original_language"
                  name="original_language"
                  value={formData.original_language || ''}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">选择语言</option>
                  <option value="en">英语</option>
                  <option value="ja">日语</option>
                  <option value="ko">韩语</option>
                  <option value="fr">法语</option>
                  <option value="de">德语</option>
                  <option value="es">西班牙语</option>
                  <option value="th">泰语</option>
                  <option value="vi">越南语</option>
                </select>
              </div>

              <div>
                <label htmlFor="target_language" className="block text-sm font-medium text-gray-700 mb-2">
                  目标语言 <span className="text-red-500">*</span>
                </label>
                <select
                  id="target_language"
                  name="target_language"
                  required
                  value={formData.target_language}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="zh">中文</option>
                  <option value="en">英语</option>
                  <option value="ja">日语</option>
                  <option value="ko">韩语</option>
                </select>
              </div>

              <div>
                <label htmlFor="year" className="block text-sm font-medium text-gray-700 mb-2">
                  年份
                </label>
                <input
                  type="number"
                  id="year"
                  name="year"
                  min={1900}
                  max={2100}
                  value={formData.year || ''}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="2024"
                />
              </div>
            </div>
          </div>

          {/* 按钮 */}
          <div className="flex items-center justify-end space-x-4 mt-6 pt-6 border-t border-gray-200">
            <Link
              to="/projects"
              className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              取消
            </Link>
            <button
              type="submit"
              disabled={isCreating}
              className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isCreating ? '创建中...' : '创建项目'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
