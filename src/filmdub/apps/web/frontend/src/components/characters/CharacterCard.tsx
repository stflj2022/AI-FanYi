import { User, Edit, Volume2, Film } from 'lucide-react'

interface CharacterCardProps {
  id: string
  name: string
  gender?: string
  ageRange?: string
  roleType?: string
  description?: string
  originalActor?: string
  avatarUrl?: string
  voiceProfilesCount?: number
  onClick?: () => void
  onEdit?: (e: React.MouseEvent) => void
}

export function CharacterCard({
  id,
  name,
  gender,
  ageRange,
  roleType,
  description,
  originalActor,
  avatarUrl,
  voiceProfilesCount = 0,
  onClick,
  onEdit,
}: CharacterCardProps) {
  const getGenderLabel = (g?: string) => {
    const labels: Record<string, string> = {
      male: '男',
      female: '女',
      other: '其他',
      unknown: '未知',
    }
    return g ? labels[g] || g : undefined
  }

  const getAgeRangeLabel = (ar?: string) => {
    const labels: Record<string, string> = {
      child: '儿童 (0-12)',
      teen: '青少年 (13-19)',
      young_adult: '青年 (20-35)',
      middle_aged: '中年 (36-55)',
      senior: '老年 (56+)',
    }
    return ar ? labels[ar] || ar : undefined
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
    return rt ? labels[rt] || rt : undefined
  }

  return (
    <div
      className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-md transition-shadow cursor-pointer"
      onClick={onClick}
    >
      {/* 头部：头像和基本信息 */}
      <div className="flex items-start gap-4">
        {/* 头像 */}
        <div className="flex-shrink-0">
          {avatarUrl ? (
            <img
              src={avatarUrl}
              alt={name}
              className="w-16 h-16 rounded-full object-cover bg-gray-100"
            />
          ) : (
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl font-medium">
              {name.charAt(0).toUpperCase()}
            </div>
          )}
        </div>

        {/* 基本信息 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between">
            <div className="min-w-0">
              <h3 className="text-lg font-semibold text-gray-900 truncate">{name}</h3>
              {originalActor && (
                <p className="text-sm text-gray-500 flex items-center gap-1 mt-1">
                  <Film size={14} />
                  原声: {originalActor}
                </p>
              )}
            </div>

            {onEdit && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onEdit(e)
                }}
                className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
                title="编辑"
              >
                <Edit size={16} className="text-gray-500" />
              </button>
            )}
          </div>

          {/* 标签 */}
          <div className="flex flex-wrap gap-2 mt-2">
            {gender && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
                <User size={12} />
                {getGenderLabel(gender)}
              </span>
            )}
            {ageRange && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700">
                {getAgeRangeLabel(ageRange)}
              </span>
            )}
            {roleType && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-50 text-purple-700">
                {getRoleTypeLabel(roleType)}
              </span>
            )}
            {voiceProfilesCount > 0 && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-orange-50 text-orange-700">
                <Volume2 size={12} />
                {voiceProfilesCount} 个音色
              </span>
            )}
          </div>
        </div>
      </div>

      {/* 描述 */}
      {description && (
        <p className="mt-3 text-sm text-gray-600 line-clamp-2">{description}</p>
      )}
    </div>
  )
}
