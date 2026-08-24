import { useState, useEffect } from 'react'
import { useNavigate, Link, useParams } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { projectAPI } from '../services/projectAPI'
import type { ProjectCreate, ProjectUpdate } from '../types'

type ProjectFormData = Omit<ProjectCreate, 'config'> & {
  config?: string
}

export function ProjectForm() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const isEdit = !!id

  const [formData, setFormData] = useState<ProjectFormData>({
    name: '',
    description: '',
    media_type: '',
    title: '',
    title_en: '',
    season: undefined,
    episode: undefined,
    year: undefined,
    original_language: '',
    target_language: 'zh-CN',
    tmdb_id: undefined,
    imdb_id: '',
    config: '',
  })

  const [errors, setErrors] = useState<Record<string, string>>({})

  // 获取项目详情（编辑模式）
  const { data: project, isLoading } = useQuery({
    queryKey: ['project', id],
    queryFn: () => projectAPI.get(id!),
    enabled: isEdit,
  })

  // 加载项目数据到表单
  useEffect(() => {
    if (project) {
      setFormData({
        name: project.name,
        description: project.description || '',
        media_type: project.media_type || '',
        title: project.title || '',
        title_en: project.title_en || '',
        season: project.season || undefined,
        episode: project.episode || undefined,
        year: project.year || undefined,
        original_language: project.original_language || '',
        target_language: project.target_language,
        tmdb_id: project.tmdb_id || undefined,
        imdb_id: project.imdb_id || '',
        config: project.config ? JSON.stringify(project.config, null, 2) : '',
      })
    }
  }, [project])

  // 创建项目
  const createMutation = useMutation({
    mutationFn: (data: ProjectCreate) => projectAPI.create(data),
    onSuccess: (result) => {
      navigate(`/projects/${result.id}`)
    },
  })

  // 更新项目
  const updateMutation = useMutation({
    mutationFn: (data: ProjectUpdate) => projectAPI.update(id!, data),
    onSuccess: (result) => {
      navigate(`/projects/${result.id}`)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    // 验证
    const newErrors: Record<string, string> = {}

    if (!formData.name.trim()) {
      newErrors.name = '项目名称不能为空'
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors)
      return
    }

    // 准备数据
    const data: ProjectCreate | ProjectUpdate = {
      name: formData.name,
      description: formData.description || undefined,
      media_type: formData.media_type || undefined,
      title: formData.title || undefined,
      title_en: formData.title_en || undefined,
      season: formData.season || undefined,
      episode: formData.episode || undefined,
      year: formData.year || undefined,
      original_language: formData.original_language || undefined,
      target_language: formData.target_language,
      tmdb_id: formData.tmdb_id || undefined,
      imdb_id: formData.imdb_id || undefined,
    }

    // 解析 config
    if (formData.config) {
      try {
        data.config = JSON.parse(formData.config)
      } catch {
        newErrors.config = '配置必须是有效的 JSON 格式'
        setErrors(newErrors)
        return
      }
    }

    // 提交
    if (isEdit) {
      updateMutation.mutate(data)
    } else {
      createMutation.mutate(data as ProjectCreate)
    }
  }

  const handleChange = (field: string, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    // 清除该字段的错误
    if (errors[field]) {
      setErrors((prev) => {
        const newErrors = { ...prev }
        delete newErrors[field]
        return newErrors
      })
    }
  }

  if (isEdit && isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-6">
          <Link
            to="/projects"
            className="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
          >
            ← 返回项目列表
          </Link>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              {isEdit ? '编辑项目' : '新建项目'}
            </h1>
          </div>

          <form onSubmit={handleSubmit} className="p-6 space-y-6">
            {/* 基本信息 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  项目名称 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => handleChange('name', e.target.value)}
                  className={`w-full px-4 py-2 border rounded-md focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white ${
                    errors.name ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
                  }`}
                  placeholder="例如：权力的游戏 第一季中文配音"
                />
                {errors.name && (
                  <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.name}</p>
                )}
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  项目描述
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => handleChange('description', e.target.value)}
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                  placeholder="简要描述项目内容..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  媒体类型
                </label>
                <input
                  type="text"
                  value={formData.media_type}
                  onChange={(e) => handleChange('media_type', e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                  placeholder="例如：TV Series, Movie"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  目标语言 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.target_language}
                  onChange={(e) => handleChange('target_language', e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                  placeholder="例如：zh-CN"
                />
              </div>
            </div>

            {/* 影片信息 */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                影片信息
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    标题
                  </label>
                  <input
                    type="text"
                    value={formData.title}
                    onChange={(e) => handleChange('title', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                    placeholder="中文标题"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    英文标题
                  </label>
                  <input
                    type="text"
                    value={formData.title_en}
                    onChange={(e) => handleChange('title_en', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                    placeholder="English Title"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    季数
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={formData.season || ''}
                    onChange={(e) => handleChange('season', e.target.value ? parseInt(e.target.value) : undefined)}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                    placeholder="1"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    集数
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={formData.episode || ''}
                    onChange={(e) => handleChange('episode', e.target.value ? parseInt(e.target.value) : undefined)}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                    placeholder="1"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    年份
                  </label>
                  <input
                    type="number"
                    min="1900"
                    max="2100"
                    value={formData.year || ''}
                    onChange={(e) => handleChange('year', e.target.value ? parseInt(e.target.value) : undefined)}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                    placeholder="2024"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    原始语言
                  </label>
                  <input
                    type="text"
                    value={formData.original_language}
                    onChange={(e) => handleChange('original_language', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                    placeholder="例如：en-US"
                  />
                </div>
              </div>
            </div>

            {/* 外部数据源 */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                外部数据源
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    TMDB ID
                  </label>
                  <input
                    type="number"
                    value={formData.tmdb_id || ''}
                    onChange={(e) => handleChange('tmdb_id', e.target.value ? parseInt(e.target.value) : undefined)}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                    placeholder="例如：1399"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    IMDB ID
                  </label>
                  <input
                    type="text"
                    value={formData.imdb_id}
                    onChange={(e) => handleChange('imdb_id', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
                    placeholder="例如：tt0944947"
                  />
                </div>
              </div>
            </div>

            {/* 配置 */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                配置（JSON）
              </h3>
              <textarea
                value={formData.config}
                onChange={(e) => handleChange('config', e.target.value)}
                rows={6}
                className={`w-full px-4 py-2 border rounded-md font-mono text-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white ${
                  errors.config ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
                }`}
                placeholder='{ "key": "value" }'
              />
              {errors.config && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.config}</p>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-4 pt-6 border-t border-gray-200 dark:border-gray-700">
              <Link
                to="/projects"
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                取消
              </Link>
              <button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
                className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {createMutation.isPending || updateMutation.isPending
                  ? '保存中...'
                  : isEdit
                  ? '保存修改'
                  : '创建项目'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
