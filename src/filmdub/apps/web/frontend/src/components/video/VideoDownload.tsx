import { useState } from 'react'
import { Download, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { Button } from '../ui/button'

interface VideoDownloadProps {
  downloadUrl: string
  filename?: string
  onSuccess?: () => void
  onError?: (error: Error) => void
}

type DownloadStatus = 'idle' | 'downloading' | 'completed' | 'error'

export function VideoDownload({
  downloadUrl,
  filename = 'video.mp4',
  onSuccess,
  onError,
}: VideoDownloadProps) {
  const [status, setStatus] = useState<DownloadStatus>('idle')
  const [progress, setProgress] = useState(0)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const handleDownload = async () => {
    try {
      setStatus('downloading')
      setProgress(0)
      setErrorMessage(null)

      const response = await fetch(downloadUrl)
      if (!response.ok) {
        throw new Error(`Download failed: ${response.statusText}`)
      }

      const contentLength = response.headers.get('content-length')
      const total = contentLength ? parseInt(contentLength, 10) : 0

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('Failed to get reader')
      }

      const chunks: Uint8Array[] = []
      let receivedLength = 0

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        chunks.push(value)
        receivedLength += value.length

        if (total > 0) {
          setProgress(Math.round((receivedLength / total) * 100))
        }
      }

      // 合并所有 chunk
      const blob = new Blob(chunks, { type: 'video/mp4' })

      // 创建下载链接
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)

      setStatus('completed')
      onSuccess?.()
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Unknown error')
      setErrorMessage(err.message)
      setStatus('error')
      onError?.(err)
    }
  }

  const getStatusIcon = () => {
    switch (status) {
      case 'downloading':
        return <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent" />
      case 'completed':
        return <CheckCircle size={20} />
      case 'error':
        return <XCircle size={20} />
      default:
        return <Download size={20} />
    }
  }

  const getStatusText = () => {
    switch (status) {
      case 'downloading':
        return `下载中 ${progress}%`
      case 'completed':
        return '下载完成'
      case 'error':
        return '下载失败'
      default:
        return '下载视频'
    }
  }

  return (
    <div className="space-y-3">
      <Button
        onClick={handleDownload}
        disabled={status === 'downloading'}
        className="w-full flex items-center justify-center gap-2"
        variant={status === 'error' ? 'destructive' : 'default'}
      >
        {getStatusIcon()}
        {getStatusText()}
      </Button>

      {/* 进度条 */}
      {status === 'downloading' && (
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* 错误信息 */}
      {status === 'error' && errorMessage && (
        <div className="flex items-start gap-2 text-sm text-red-600 bg-red-50 p-3 rounded-lg">
          <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* 成功信息 */}
      {status === 'completed' && (
        <div className="flex items-center gap-2 text-sm text-green-600 bg-green-50 p-3 rounded-lg">
          <CheckCircle size={16} />
          <span>视频已下载到本地</span>
        </div>
      )}
    </div>
  )
}
