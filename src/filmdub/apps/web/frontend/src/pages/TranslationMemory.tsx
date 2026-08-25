import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import apiClient from '../services/api'

interface TranslationMemoryEntry {
  id: string
  project_id: string | null
  source_text: string
  translated_text: string
  source_lang: string
  target_lang: string
  context: string | null
  character_name: string | null
  usage_count: number
  last_used: string | null
  created_at: string
  updated_at: string
}

interface GlossaryTerm {
  id: string
  project_id: string | null
  source_term: string
  target_term: string
  category: string | null
  usage_count: number
  created_at: string
  updated_at: string
}

interface Statistics {
  total_entries: number
  total_glossary_terms: number
  language_pairs: { pair: string; count: number }[]
  most_used_translations: { id: string; source: string; target: string; usage_count: number }[]
  most_used_terms: { id: string; source: string; target: string; usage_count: number }[]
}

export default function TranslationMemory() {
  const [activeTab, setActiveTab] = useState<'entries' | 'glossary' | 'statistics'>('entries')
  const [search, setSearch] = useState('')

  // 获取统计信息
  const { data: stats } = useQuery<Statistics>({
    queryKey: ['translation-memory', 'statistics'],
    queryFn: async () => {
      const response = await apiClient.get('/translation-memory/statistics')
      return response.data
    },
  })

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">翻译记忆</h1>
        <p className="text-gray-600">查看和管理翻译记忆库与术语库</p>
      </div>

      {/* 统计卡片 */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">翻译条目</div>
            <div className="mt-2 text-3xl font-bold text-blue-600">{stats.total_entries}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">术语条目</div>
            <div className="mt-2 text-3xl font-bold text-green-600">{stats.total_glossary_terms}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">语言对</div>
            <div className="mt-2 text-3xl font-bold text-purple-600">{stats.language_pairs.length}</div>
          </div>
        </div>
      )}

      {/* 标签页 */}
      <div className="bg-white shadow rounded-lg">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <button
              onClick={() => setActiveTab('entries')}
              className={`px-6 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'entries'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              翻译记忆
            </button>
            <button
              onClick={() => setActiveTab('glossary')}
              className={`px-6 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'glossary'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              术语库
            </button>
            <button
              onClick={() => setActiveTab('statistics')}
              className={`px-6 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'statistics'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              统计信息
            </button>
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'entries' && (
            <TranslationMemoryTab search={search} setSearch={setSearch} />
          )}
          {activeTab === 'glossary' && (
            <GlossaryTab search={search} setSearch={setSearch} />
          )}
          {activeTab === 'statistics' && stats && <StatisticsTab stats={stats} />}
        </div>
      </div>
    </div>
  )
}

function TranslationMemoryTab({ search, setSearch }: { search: string; setSearch: (s: string) => void }) {
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['translation-memory', 'entries', page, search],
    queryFn: async () => {
      const params: any = { page, page_size: 20 }
      if (search) params.search = search
      const response = await apiClient.get('/translation-memory/entries', { params })
      return response.data
    },
  })

  return (
    <div>
      <div className="mb-4 flex gap-4">
        <input
          type="text"
          placeholder="搜索原文或译文..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {isLoading ? (
        <div className="text-center py-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : data && data.items.length > 0 ? (
        <div className="space-y-4">
          {data.items.map((entry: TranslationMemoryEntry) => (
            <div key={entry.id} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50">
              <div className="flex justify-between items-start mb-2">
                <div className="flex-1">
                  <div className="text-sm text-gray-500 mb-1">
                    {entry.source_lang} → {entry.target_lang}
                  </div>
                  <div className="text-lg font-medium text-gray-900">{entry.source_text}</div>
                  <div className="text-lg text-blue-600 mt-1">{entry.translated_text}</div>
                  {entry.context && (
                    <div className="text-sm text-gray-500 mt-2 italic">"{entry.context}"</div>
                  )}
                </div>
                <div className="text-right ml-4">
                  <div className="text-sm text-gray-500">使用 {entry.usage_count} 次</div>
                  {entry.character_name && (
                    <div className="text-sm text-gray-500">{entry.character_name}</div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">暂无翻译记忆数据</div>
      )}
    </div>
  )
}

function GlossaryTab({ search, setSearch }: { search: string; setSearch: (s: string) => void }) {
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['translation-memory', 'glossary', page, search],
    queryFn: async () => {
      const params: any = { page, page_size: 20 }
      if (search) params.search = search
      const response = await apiClient.get('/translation-memory/glossary', { params })
      return response.data
    },
  })

  return (
    <div>
      <div className="mb-4 flex gap-4">
        <input
          type="text"
          placeholder="搜索术语..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {isLoading ? (
        <div className="text-center py-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : data && data.items.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.items.map((term: GlossaryTerm) => (
            <div key={term.id} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="text-lg font-medium text-gray-900">{term.source_term}</div>
                  <div className="text-lg text-blue-600 mt-1">{term.target_term}</div>
                  {term.category && (
                    <div className="mt-2">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                        {term.category}
                      </span>
                    </div>
                  )}
                </div>
                <div className="text-right ml-4 text-sm text-gray-500">
                  使用 {term.usage_count} 次
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">暂无术语数据</div>
      )}
    </div>
  )
}

function StatisticsTab({ stats }: { stats: Statistics }) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-3">语言对分布</h3>
        <div className="space-y-2">
          {stats.language_pairs.map((pair, index) => (
            <div key={index} className="flex justify-between items-center p-3 bg-gray-50 rounded">
              <span className="text-gray-700">{pair.pair}</span>
              <span className="font-medium text-gray-900">{pair.count} 条</span>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-3">最常用翻译</h3>
        <div className="space-y-2">
          {stats.most_used_translations.slice(0, 5).map((item, index) => (
            <div key={index} className="p-3 bg-gray-50 rounded">
              <div className="text-sm text-gray-600">{item.source}</div>
              <div className="text-sm text-blue-600 mt-1">{item.target}</div>
              <div className="text-xs text-gray-500 mt-1">使用 {item.usage_count} 次</div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-3">最常用术语</h3>
        <div className="space-y-2">
          {stats.most_used_terms.slice(0, 5).map((item, index) => (
            <div key={index} className="flex justify-between items-center p-3 bg-gray-50 rounded">
              <div>
                <div className="text-sm text-gray-900">{item.source}</div>
                <div className="text-sm text-blue-600">{item.target}</div>
              </div>
              <div className="text-xs text-gray-500">使用 {item.usage_count} 次</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
