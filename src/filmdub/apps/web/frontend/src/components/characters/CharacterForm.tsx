import { useState, useEffect } from 'react'
import { User, Calendar, Film, X, Upload } from 'lucide-react'
import { Button } from '../ui/button'

interface CharacterFormProps {
  characterId?: string
  projectId: string
  onSave: (data: any) => Promise<void>
  onCancel: () => void
}

export function CharacterForm({ characterId, projectId, onSave, onCancel }: CharacterFormProps) {
  const [loading, setLoading] = useState(false)
  const [uploadingAvatar, setUploadingAvatar] = useState(false)

  const [formData, setFormData] = useState({
    name: '',
    gender: '',
    age_range: '',
    role_type: '',
    description: '',
    original_actor: '',
    avatar_url: '',
  })

  useEffect(() => {
    if (characterId) {
      fetchCharacter()
    }
  }, [characterId])

  const fetchCharacter = async () => {
    try {
      const response = await fetch(`/api/v1/characters/${characterId}`)
      if (!response.ok) throw new Error('Failed to fetch character')

      const data = await response.json()
      setFormData({
        name: data.name || '',
        gender: data.gender || '',
        age_range: data.age_range || '',
        role_type: data.role_type || '',
        description: data.description || '',
        original_actor: data.original_actor || '',
        avatar_url: data.avatar_url || '',
      })
    } catch (error) {
      console.error('Failed to fetch character:', error)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setLoading(true)
      await onSave(formData)
    } catch (error) {
      console.error('Failed to save character:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      setUploadingAvatar(true)
      const formData = new FormData()
      formData.append('file', file)

      const url = characterId
        ? `/api/v1/characters/${characterId}/avatar`
        : `/api/v1/characters/${projectId}/avatar`

      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) throw new Error('Failed to upload avatar')

      const data = await response.json()
      setFormData((prev) => ({ ...prev, avatar_url: data.avatar_url }))
    } catch (error) {
      console.error('Failed to upload avatar:', error)
    } finally {
      setUploadingAvatar(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">
          {characterId ? '编辑人物' : '新建人物'}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* 头像上传 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">头像</label>
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0">
                {formData.avatar_url ? (
                  <img
                    src={formData.avatar_url}
                    alt="Avatar"
                    className="w-24 h-24 rounded-full object-cover bg-gray-100"
                  />
                ) : (
                  <div className="w-24 h-24 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-2xl font-bold">
                    {formData.name.charAt(0).toUpperCase() || '?'}
                  </div>
                )}
              </div>
              <div className="flex-1">
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleAvatarUpload}
                  disabled={uploadingAvatar}
                  className="hidden"
                  id="avatar-upload"
                />
                <label
                  htmlFor="avatar-upload"
                  className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 cursor-pointer"
                >
                  <Upload size={16} />
                  {uploadingAvatar ? '上传中...' : '上传头像'}
                </label>
                <p className="text-xs text-gray-500 mt-1">
                  支持 JPG、PNG、GIF 格式，最大 5MB
                </p>
              </div>
            </div>
          </div>

          {/* 名称 */}
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
              人物名称 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="name"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="请输入人物名称"
            />
          </div>

          {/* 原声演员 */}
          <div>
            <label htmlFor="original_actor" className="block text-sm font-medium text-gray-700 mb-2">
              原声演员
            </label>
            <div className="relative">
              <Film className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
              <input
                type="text"
                id="original_actor"
                value={formData.original_actor}
                onChange={(e) => setFormData({ ...formData, original_actor: e.target.value })}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="请输入原声演员名称"
              />
            </div>
          </div>

          {/* 性别和年龄段 */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="gender" className="block text-sm font-medium text-gray-700 mb-2">
                性别
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                <select
                  id="gender"
                  value={formData.gender}
                  onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">未知</option>
                  <option value="male">男</option>
                  <option value="female">女</option>
                  <option value="other">其他</option>
                </select>
              </div>
            </div>

            <div>
              <label htmlFor="age_range" className="block text-sm font-medium text-gray-700 mb-2">
                年龄段
              </label>
              <select
                id="age_range"
                value={formData.age_range}
                onChange={(e) => setFormData({ ...formData, age_range: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">未知</option>
                <option value="child">儿童 (0-12)</option>
                <option value="teen">青少年 (13-19)</option>
                <option value="young_adult">青年 (20-35)</option>
                <option value="middle_aged">中年 (36-55)</option>
                <option value="senior">老年 (56+)</option>
              </select>
            </div>
          </div>

          {/* 角色类型 */}
          <div>
            <label htmlFor="role_type" className="block text-sm font-medium text-gray-700 mb-2">
              角色类型
            </label>
            <select
              id="role_type"
              value={formData.role_type}
              onChange={(e) => setFormData({ ...formData, role_type: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">未知</option>
              <option value="protagonist">主角</option>
              <option value="antagonist">反派</option>
              <option value="supporting">配角</option>
              <option value="extras">群演</option>
              <option value="narrator">旁白</option>
              <option value="other">其他</option>
            </select>
          </div>

          {/* 描述 */}
          <div>
            <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
              人物描述
            </label>
            <textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="请输入人物描述..."
            />
          </div>

          {/* 按钮 */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
            <Button type="button" variant="outline" onClick={onCancel}>
              <X size={18} className="mr-2" />
              取消
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? '保存中...' : characterId ? '更新' : '创建'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
