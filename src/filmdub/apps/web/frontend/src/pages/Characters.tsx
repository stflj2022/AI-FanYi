import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import apiClient from '../services/api'

interface Character {
  id: string
  name: string
  gender: string | null
  age_range: string | null
  role_type: string | null
  description: string | null
  original_actor: string | null
  avatar_url: string | null
  voice_profiles: VoiceProfile[]
  created_at: string
  updated_at: string
}

interface VoiceProfile {
  id: string
  character_id: string
  voice_id: string
  provider: string
  model: string | null
  style: string | null
  similarity_score: number | null
  is_active: boolean
  created_at: string
  updated_at: string
}

interface CharactersListResponse {
  total: number
  page: number
  page_size: number
  items: Character[]
}

export default function Characters() {
  const { projectId } = useParams()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')

  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery<CharactersListResponse>({
    queryKey: ['characters', projectId, page, search],
    queryFn: async () => {
      const params: any = { page, page_size: 20 }
      if (projectId) params.project_id = projectId
      if (search) params.search = search

      const response = await apiClient.get('/characters', { params })
      return response.data
    },
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
  }

  const getVoiceStatus = (character: Character) => {
    if (!character.voice_profiles || character.voice_profiles.length === 0) {
      return { status: '未建立', color: 'gray' }
    }
    const activeProfile = character.voice_profiles.find(p => p.is_active)
    if (activeProfile) {
      return { status: '已建立', color: 'green' }
    }
    return { status: '待激活', color: 'yellow' }
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">人物数据库</h1>
        <p className="text-gray-600">查看和管理项目中的人物信息及音色状态</p>
      </div>

      {/* 搜索栏 */}
      <form onSubmit={handleSearch} className="mb-6 flex gap-4">
        <input
          type="text"
          placeholder="搜索人物姓名或描述..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="submit"
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          搜索
        </button>
      </form>

      {/* 人物列表 */}
      {isLoading ? (
        <div className="text-center py-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-gray-600">加载中...</p>
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">加载失败，请稍后重试</p>
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <div className="bg-white shadow rounded-lg overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    人物
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    原声演员
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    音色状态
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    类型
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {data.items.map((character) => {
                  const voiceStatus = getVoiceStatus(character)
                  return (
                    <tr key={character.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          {character.avatar_url && (
                            <img
                              src={character.avatar_url}
                              alt={character.name}
                              className="h-10 w-10 rounded-full mr-3"
                            />
                          )}
                          <div>
                            <div className="text-sm font-medium text-gray-900">{character.name}</div>
                            {character.description && (
                              <div className="text-sm text-gray-500 truncate max-w-xs">
                                {character.description}
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {character.original_actor || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-${voiceStatus.color}-100 text-${voiceStatus.color}-800`}
                        >
                          {voiceStatus.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {character.role_type || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <Link
                          to={`/characters/${character.id}`}
                          className="text-blue-600 hover:text-blue-900 mr-3"
                        >
                          查看
                        </Link>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* 分页 */}
          <div className="mt-4 flex items-center justify-between">
            <div className="text-sm text-gray-700">
              共 {data.total} 条记录
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                上一页
              </button>
              <span className="px-4 py-2 text-gray-700">
                第 {page} 页
              </span>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={page * data.page_size >= data.total}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                下一页
              </button>
            </div>
          </div>
        </>
      ) : (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
          <p className="text-gray-600">暂无人物数据</p>
        </div>
      )}
    </div>
  )
}
