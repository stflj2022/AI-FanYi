export function Dashboard() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

      {/* 快速操作 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="p-6 bg-white rounded-lg border border-gray-200">
          <h2 className="text-lg font-semibold mb-2">添加视频</h2>
          <p className="text-gray-600 mb-4">上传视频开始新的配音任务</p>
          <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors">
            开始上传
          </button>
        </div>

        <div className="p-6 bg-white rounded-lg border border-gray-200">
          <h2 className="text-lg font-semibold mb-2">创建项目</h2>
          <p className="text-gray-600 mb-4">组织你的配音项目</p>
          <button className="px-4 py-2 bg-gray-200 text-gray-900 rounded-md hover:bg-gray-300 transition-colors">
            新建项目
          </button>
        </div>

        <div className="p-6 bg-white rounded-lg border border-gray-200">
          <h2 className="text-lg font-semibold mb-2">系统状态</h2>
          <p className="text-gray-600 mb-4">查看平台运行状态</p>
          <button className="px-4 py-2 bg-gray-200 text-gray-900 rounded-md hover:bg-gray-300 transition-colors">
            查看状态
          </button>
        </div>
      </div>

      {/* 最近任务 */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold">最近任务</h2>
        </div>
        <div className="p-6">
          <p className="text-gray-500">暂无最近任务</p>
        </div>
      </div>
    </div>
  )
}
