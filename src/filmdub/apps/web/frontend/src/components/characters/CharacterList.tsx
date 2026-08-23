import { useState, useEffect } from 'react'
import { Search, Filter, Plus, User } from 'lucide-react'
import { CharacterCard } from './CharacterCard'
import { Button } from '../ui/button'

interface Character {
  id: string
  name: string
  gender?: string
  age_range?: string
  role_type?: string
  description?: string
  original_actor?: string
  avatar_url?: string
  voice_profiles_count?: number
}

interface CharacterListProps {
  projectId?: string
  onCharacterClick?: (characterId: string) => void
  onCharacterEdit?: (characterId: string) => void
  onCreateCharacter?: () => void
}

export function CharacterList({
  projectId,
  onCharacterClick,
  onCharacterEdit,
  onCreateCharacter,
}: CharacterListProps) {
  const [characters, setCharacters] = useState<Character[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [genderFilter, setGenderFilter] = useState('')
  const [ageRangeFilter, setAgeRangeFilter] = useState('')
  const [roleTypeFilter, setRoleTypeFilter] = useState('')
  const [showFilters, setShowFilters] = useState(false)

  // 获取人物列表
  const fetchCharacters = async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams()
      if (projectId) params.append('project_id', projectId)
      if (search) params.append('search', search)
      if (genderFilter) params.append('gender', genderFilter)
      if (ageRangeFilter) params.append('age_range', ageRangeFilter)
      if (roleTypeFilter) params.append('role_type', roleTypeFilter)

      const response = await fetch(`/api/v1/characters?${params}`)
      if (!response.ok) throw new Error('Failed to fetch characters')

      const data = await response.json()
      setCharacters(data.items || [])
    } catch (error) {
      console.error('Failed to fetch characters:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCharacters()
  }, [projectId, search, genderFilter, ageRangeFilter, roleTypeFilter])

  const handleSearchChange = (value: string) => {
    setSearch(value)
  }

  return (
    <div className="space-y-4">
      {/* 工具栏 */}
      <div className="flex items-center gap-3">
        {/* 搜索框 */}
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input
            type="text"
            placeholder="搜索人物名称或描述..."
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* 筛选按钮 */}
        <Button
          variant="outline"
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center gap-2"
        >
          <Filter size={18} />
          筛选
        </Button>

        {/* 创建按钮 */}
        {onCreateCharacter && (
          <Button onClick={onCreateCharacter} className="flex items-center gap-2">
            <Plus size={18} />
            新建人物
          </Button>
        )}
      </div>

      {/* 筛选面板 */}
      {showFilters && (
        <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* 性别筛选 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">性别</label>
              <select
                value={genderFilter}
                onChange={(e) => setGenderFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">全部</option>
                <option value="male">男</option>
                <option value="female">女</option>
                <option value="other">其他</option>
                <option value="unknown">未知</option>
              </select>
            </div>

            {/* 年龄段筛选 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">年龄段</label>
              <select
                value={ageRangeFilter}
                onChange={(e) => setAgeRangeFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">全部</option>
                <option value="child">儿童 (0-12)</option>
                <option value="teen">青少年 (13-19)</option>
                <option value="young_adult">青年 (20-35)</option>
                <option value="middle_aged">中年 (36-55)</option>
                <option value="senior">老年 (56+)</option>
              </select>
            </div>

            {/* 角色类型筛选 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">角色类型</label>
              <select
                value={roleTypeFilter}
                onChange={(e) => setRoleTypeFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">全部</option>
                <option value="protagonist">主角</option>
                <option value="antagonist">反派</option>
                <option value="supporting">配角</option>
                <option value="extras">群演</option>
                <option value="narrator">旁白</option>
                <option value="other">其他</option>
              </select>
            </div>
          </div>

          {/* 清除筛选 */}
          {(genderFilter || ageRangeFilter || roleTypeFilter) && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setGenderFilter('')
                  setAgeRangeFilter('')
                  setRoleTypeFilter('')
                }}
              >
                清除筛选
              </Button>
            </div>
          )}
        </div>
      )}

      {/* 加载状态 */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      )}

      {/* 空状态 */}
      {!loading && characters.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <User size={48} className="text-gray-300 mb-3" />
          <h3 className="text-lg font-medium text-gray-900">暂无人物</h3>
          <p className="text-gray-500 mt-1">
            {search || genderFilter || ageRangeFilter || roleTypeFilter
              ? '没有找到匹配的人物'
              : '开始创建第一个人物吧'}
          </p>
          {onCreateCharacter && !search && !genderFilter && !ageRangeFilter && !roleTypeFilter && (
            <Button onClick={onCreateCharacter} className="mt-4">
              <Plus size={18} className="mr-2" />
              新建人物
            </Button>
          )}
        </div>
      )}

      {/* 人物列表 */}
      {!loading && characters.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {characters.map((character) => (
            <CharacterCard
              key={character.id}
              id={character.id}
              name={character.name}
              gender={character.gender}
              ageRange={character.age_range}
              roleType={character.role_type}
              description={character.description}
              originalActor={character.original_actor}
              avatarUrl={character.avatar_url}
              voiceProfilesCount={character.voice_profiles_count}
              onClick={() => onCharacterClick?.(character.id)}
              onEdit={(e) => onCharacterEdit?.(character.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
