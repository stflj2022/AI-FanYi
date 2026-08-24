import { useState, useEffect, useCallback } from 'react'
import { QuickActionsCard } from '../components/dashboard/QuickActionsCard'
import { JobStatsCard } from '../components/dashboard/JobStatsCard'
import { RecentJobsList } from '../components/dashboard/RecentJobsList'
import jobAPI from '../services/jobAPI'
import type { JobResponse, JobStatsResponse } from '../services/jobAPI'
import { useDashboardEvents } from '../hooks/use-dashboard-events'
import { useBrowserNotification } from '../hooks/use-browser-notification'

export function Dashboard() {
  const [stats, setStats] = useState<JobStatsResponse | null>(null)
  const [recentJobs, setRecentJobs] = useState<JobResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshKey, setRefreshKey] = useState(0)

  // 浏览器通知
  const { requestPermission, sendNotification } = useBrowserNotification()

  // 加载统计数据
  const loadStats = useCallback(async () => {
    try {
      const data = await jobAPI.getJobStats()
      setStats(data)
    } catch (error) {
      console.error('Failed to load job stats:', error)
    }
  }, [])

  // 加载最近任务
  const loadRecentJobs = useCallback(async () => {
    try {
      const data = await jobAPI.getRecentJobs(10)
      setRecentJobs(data.items)
    } catch (error) {
      console.error('Failed to load recent jobs:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  // 初始加载
  useEffect(() => {
    Promise.all([loadStats(), loadRecentJobs()])

    // 请求通知权限
    requestPermission()
  }, [loadStats, loadRecentJobs, requestPermission])

  // WebSocket 事件监听
  const { isConnected } = useDashboardEvents({
    onJobCreated: (event) => {
      console.log('Job created:', event)
      // 刷新数据
      setRefreshKey((prev) => prev + 1)
      sendNotification({
        title: '新任务已创建',
        body: event.data.job_name,
      })
    },
    onJobStatusChanged: (event) => {
      console.log('Job status changed:', event)
      // 刷新数据
      setRefreshKey((prev) => prev + 1)
      if (event.data.new_status === 'completed') {
        sendNotification({
          title: '任务已完成',
          body: `任务 ${event.data.job_id} 已完成`,
        })
      } else if (event.data.new_status === 'failed') {
        sendNotification({
          title: '任务失败',
          body: `任务 ${event.data.job_id} 执行失败`,
        })
      }
    },
    onAnyEvent: () => {
      // 任何事件都触发数据刷新
      Promise.all([loadStats(), loadRecentJobs()])
    },
  })

  // 当 refreshKey 变化时刷新数据
  useEffect(() => {
    if (refreshKey > 0) {
      Promise.all([loadStats(), loadRecentJobs()])
    }
  }, [refreshKey, loadStats, loadRecentJobs])

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">仪表盘</h1>
          <p className="text-sm text-gray-500 mt-1">
            {isConnected ? '🟢 实时连接' : '🔴 离线'}
          </p>
        </div>
      </div>

      {/* 任务统计 */}
      {stats && <JobStatsCard stats={stats} loading={loading} />}

      {/* 快速操作 */}
      <QuickActionsCard />

      {/* 最近任务 */}
      <RecentJobsList jobs={recentJobs} loading={loading} />
    </div>
  )
}
