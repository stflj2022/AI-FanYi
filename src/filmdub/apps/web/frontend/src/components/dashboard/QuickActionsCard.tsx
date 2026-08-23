import { Link } from 'react-router-dom'

export function QuickActionsCard() {
  const actions = [
    {
      title: '添加视频',
      description: '上传视频开始新的配音任务',
      icon: '📹',
      to: '/upload',
      color: 'bg-blue-600 hover:bg-blue-700',
      borderColor: 'border-blue-200',
    },
    {
      title: '创建项目',
      description: '组织你的配音项目',
      icon: '📁',
      to: '/projects/new',
      color: 'bg-gray-200 hover:bg-gray-300 text-gray-900',
      borderColor: 'border-gray-200',
    },
    {
      title: '查看项目',
      description: '浏览所有项目',
      icon: '🎬',
      to: '/projects',
      color: 'bg-gray-200 hover:bg-gray-300 text-gray-900',
      borderColor: 'border-gray-200',
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
      {actions.map((action) => (
        <Link
          key={action.title}
          to={action.to}
          className={`p-6 bg-white rounded-lg border ${action.borderColor} transition-all hover:shadow-md`}
        >
          <div className="text-4xl mb-3">{action.icon}</div>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">
            {action.title}
          </h2>
          <p className="text-gray-600 mb-4">{action.description}</p>
          <button
            className={`px-4 py-2 rounded-md transition-colors ${action.color}`}
          >
            {action.title}
          </button>
        </Link>
      ))}
    </div>
  )
}
