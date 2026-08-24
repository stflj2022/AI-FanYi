import { useState, useEffect } from 'react'
import { useJobProgress } from '../hooks/use-job-progress'

interface OutputVideoProps {
  jobId: string
  projectId: string
  token?: string
}

export function OutputVideo({ jobId, projectId, token }: OutputVideoProps) {
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const [qaReport, setQaReport] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 获取输出视频和 QA 报告
  useEffect(() => {
    const fetchOutput = async () => {
      try {
        setLoading(true)
        setError(null)

        // 获取视频 URL（同源，经 nginx 反代）
        const videoResponse = await fetch(
          `/api/v1/jobs/${jobId}/output/video`,
          {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
          }
        )

        if (!videoResponse.ok) {
          throw new Error('Failed to fetch output video')
        }

        // 创建 Blob URL
        const videoBlob = await videoResponse.blob()
        const videoObjectUrl = URL.createObjectURL(videoBlob)
        setVideoUrl(videoObjectUrl)

        // 获取 QA 报告（同源）
        const qaResponse = await fetch(
          `/api/v1/jobs/${jobId}/output/qa-report`,
          {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
          }
        )

        if (qaResponse.ok) {
          const qaData = await qaResponse.json()
          setQaReport(qaData)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load output')
      } finally {
        setLoading(false)
      }
    }

    fetchOutput()
  }, [jobId, token])

  // 获取进度
  const { progress } = useJobProgress({ jobId, projectId, token })

  // 清理 Blob URL
  useEffect(() => {
    return () => {
      if (videoUrl) {
        URL.revokeObjectURL(videoUrl)
      }
    }
  }, [videoUrl])

  // 下载视频
  const handleDownload = () => {
    if (videoUrl) {
      const a = document.createElement('a')
      a.href = videoUrl
      a.download = `dubbed_video_${jobId}.mp4`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    }
  }

  if (loading) {
    return (
      <div className="output-video-container">
        <div className="loading-message">正在加载输出视频...</div>
        {progress && (
          <div className="progress-info">
            <div>当前阶段: {progress.message}</div>
            <div>进度: {Math.round(progress.progress)}%</div>
          </div>
        )}
      </div>
    )
  }

  if (error) {
    return (
      <div className="output-video-container error">
        <div className="error-message">{error}</div>
      </div>
    )
  }

  if (!videoUrl) {
    return (
      <div className="output-video-container">
        <div className="no-output-message">暂无输出视频</div>
      </div>
    )
  }

  return (
    <div className="output-video-container">
      {/* 视频播放器 */}
      <div className="video-player-wrapper">
        <video
          controls
          className="video-player"
          preload="metadata"
        >
          <source src={videoUrl} type="video/mp4" />
          您的浏览器不支持视频播放。
        </video>
      </div>

      {/* 操作按钮 */}
      <div className="video-actions">
        <button
          className="btn btn-primary"
          onClick={handleDownload}
        >
          下载视频
        </button>
      </div>

      {/* QA 报告 */}
      {qaReport && (
        <div className="qa-report-section">
          <h3>质量检查报告</h3>
          <div className="qa-score">
            <span className="qa-label">总体评分:</span>
            <span className="qa-value">{qaReport.overall_score || 'N/A'}</span>
          </div>

          {qaReport.issues && qaReport.issues.length > 0 && (
            <div className="qa-issues">
              <h4>发现的问题 ({qaReport.issues.length})</h4>
              <ul className="issues-list">
                {qaReport.issues.map((issue: any, index: number) => (
                  <li key={index} className={`issue-item ${issue.severity || 'info'}`}>
                    <span className="issue-type">{issue.type || 'General'}:</span>
                    <span className="issue-message">{issue.message || issue.description || 'No description'}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {qaReport.details && (
            <div className="qa-details">
              <h4>详细信息</h4>
              <pre className="qa-details-json">
                {JSON.stringify(qaReport.details, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
