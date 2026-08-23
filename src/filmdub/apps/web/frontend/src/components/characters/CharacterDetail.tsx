import { useState, useEffect } from 'react'
import { User, Calendar, Film, Edit, Volume2, Plus, Trash2, ArrowLeft } from 'lucide-react'
import { Button } from '../ui/button'
import { CharacterCard } from './CharacterCard'

interface VoiceProfile {
  id: string
  voice_id: string
  provider: string
  model?: string
  style?: string
  similarity_score?: number
  is_active: boolean
  created_at: string
}

interface CharacterDetailProps {
  characterId: string
  onBack?: () => void
  onEdit?: () => void
}

export function CharacterDetail({ characterId, onBack, onEdit }: CharacterDetailProps) {
  const [character, setCharacter] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchCharacter()
  }, [characterId])

  const fetchCharacter = async () => {
    try {
      setLoading(true)
      const response = await fetch(`/api/v1/characters/${characterId}`)
      if (!response.ok) throw new Error('Failed to fetch character')

      const data = await response.json()
      setCharacter(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load character')
    } finally {
      setLoading(false)
    }
  }

  const getGenderLabel = (g?: string) => {
    const labels: Record<string, string> = {
      male: '男',
      female: '女',
      other: '其他',
      unknown: '未知',
    }
    return g ? labels[g] || g : '-'
  }

  const getAgeRangeLabel = (ar?: string) => {
    const labels: Record<string, string> = {
      child: '儿童 (0-12)',
      teen: '青少年 (13-19)',
      young_adult: '青年 (20-35)',
      middle_aged: '中年 (36-55)',
      senior: '老年 (56+)',
    }
    return ar ? labels[ar] || ar : '-'
  }

  const getRoleTypeLabel = (rt?: string) => {
    const labels: Record<string, string> = {
      protagonist: '主角',
      antagonist: '反派',
      supporting: '配角',
      extras: '群演',
      narrator: '旁白',
      other: '其他',
    }
    return rt ? labels[rt] || rt : '-'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error || !character) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">{error || '人物不存在'}</p>
        {onBack && (
          <Button variant="outline" onClick={onBack} className="mt-4">
            <ArrowLeft size={18} className="mr-2" />
            返回
          </Button>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        {onBack && (
          <Button variant="ghost" onClick={onBack} className="flex items-center gap-2">
            <ArrowLeft size={18} />
            返回
          </Button>
        )}
        {onEdit && (
          <Button onClick={onEdit} className="flex items-center gap-2">
            <Edit size={18} />
            编辑人物
          </Button>
        )}
      </div>

      {/* 人物基本信息卡片 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-start gap-6">
          {/* 头像 */}
          <div className="flex-shrink-0">
            {character.avatar_url ? (
              <img
                src={character.avatar_url}
                alt={character.name}
                className="w-32 h-32 rounded-full object-cover bg-gray-100"
              />
            ) : (
              <div className="w-32 h-32 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-4xl font-bold">
                {character.name.charAt(0).toUpperCase()}
              </div>
            )}
          </div>

          {/* 基本信息 */}
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-gray-900">{character.name}</h1>

            {character.original_actor && (
              <p className="text-lg text-gray-600 flex items-center gap-2 mt-2">
                <Film size={18} />
                原声演员: {character.original_actor}
              </p>
            )}

            {character.description && (
              <p className="text-gray-700 mt-3">{character.description}</p>
            )}

            {/* 标签 */}
            <div className="flex flex-wrap gap-2 mt-4">
              <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-blue-50 text-blue-700">
                <User size={16} />
                性别: {getGenderLabel(character.gender)}
              </span>
              <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-green-50 text-green-700">
                年龄: {getAgeRangeLabel(character.age_range)}
              </span>
              <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-purple-50 text-purple-700">
                角色: {getRoleTypeLabel(character.role_type)}
              </span>
            </div>
          </div>
        </div>

        {/* 创建时间 */}
        <div className="mt-6 pt-6 border-t border-gray-200 flex items-center gap-2 text-sm text-gray-500">
          <Calendar size={16} />
          创建于 {new Date(character.created_at).toLocaleString('zh-CN')}
        </div>
      </div>

      {/* 音色档案 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Volume2 size={24} />
            音色档案
          </h2>
          <Button size="sm" className="flex items-center gap-2">
            <Plus size={16} />
            添加音色
          </Button>
        </div>

        {character.voice_profiles && character.voice_profiles.length > 0 ? (
          <div className="space-y-3">
            {character.voice_profiles.map((profile: VoiceProfile) => (
              <div
                key={profile.id}
                className="p-4 bg-gray-50 rounded-lg border border-gray-200 flex items-center justify-between"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{profile.voice_id}</span>
                    {profile.is_active && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
                        激活
                      </span>
                    )}
                  </div>
                  <div className="text-sm text-gray-600 mt-1">
                    提供商: {profile.provider}
                    {profile.model && ` | 模型: ${profile.model}`}
                    {profile.style && ` | 风格: ${profile.style}`}
                  </div>
                  {profile.similarity_score !== undefined && (
                    <div className="mt-2">
                      <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
                        <span>相似度</span>
                        <span>{(profile.similarity_score * 100).toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full"
                          style={{ width: `${profile.similarity_score * 100}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
                <Button variant="ghost" size="sm">
                  <Trash2 size={16} className="text-red-500" />
                </Button>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <Volume2 size={48} className="mx-auto text-gray-300 mb-3" />
            <p>暂无音色档案</p>
            <Button variant="outline" size="sm" className="mt-3 flex items-center gap-2 mx-auto">
              <Plus size={16} />
              添加第一个音色
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
