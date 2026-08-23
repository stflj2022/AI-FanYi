import { useRef, useState, useEffect } from 'react'
import { Play } from 'lucide-react'

interface VideoThumbnailProps {
  src: string
  time?: number
  width?: number
  height?: number
  onClick?: () => void
  showPlayOverlay?: boolean
  className?: string
}

export function VideoThumbnail({
  src,
  time = 1,
  width = 320,
  height = 180,
  onClick,
  showPlayOverlay = true,
  className = '',
}: VideoThumbnailProps) {
  const [thumbnailUrl, setThumbnailUrl] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const video = document.createElement('video')
    video.src = src
    video.crossOrigin = 'anonymous'
    video.currentTime = time
    video.muted = true

    video.addEventListener('seeked', () => {
      const canvas = canvasRef.current
      if (!canvas) return

      const ctx = canvas.getContext('2d')
      if (!ctx) return

      canvas.width = width
      canvas.height = height

      try {
        // 计算视频的宽高比
        const videoRatio = video.videoWidth / video.videoHeight
        const canvasRatio = width / height

        let drawWidth, drawHeight, drawX, drawY

        if (videoRatio > canvasRatio) {
          // 视频更宽，以高度为基准
          drawHeight = height
          drawWidth = height * videoRatio
          drawX = (width - drawWidth) / 2
          drawY = 0
        } else {
          // 视频更高，以宽度为基准
          drawWidth = width
          drawHeight = width / videoRatio
          drawX = 0
          drawY = (height - drawHeight) / 2
        }

        // 绘制视频帧
        ctx.fillStyle = '#000'
        ctx.fillRect(0, 0, width, height)
        ctx.drawImage(video, drawX, drawY, drawWidth, drawHeight)

        // 生成缩略图 URL
        const dataUrl = canvas.toDataURL('image/jpeg', 0.8)
        setThumbnailUrl(dataUrl)
        setIsLoading(false)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to generate thumbnail')
        setIsLoading(false)
      }
    })

    video.addEventListener('error', () => {
      setError('Failed to load video')
      setIsLoading(false)
    })

    return () => {
      video.remove()
    }
  }, [src, time, width, height])

  if (isLoading) {
    return (
      <div
        className={`bg-gray-200 animate-pulse flex items-center justify-center ${className}`}
        style={{ width, height }}
      >
        <div className="animate-spin rounded-full h-8 w-8 border-4 border-gray-400 border-t-transparent"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div
        className={`bg-gray-100 flex items-center justify-center text-gray-500 ${className}`}
        style={{ width, height }}
      >
        <span className="text-sm">加载失败</span>
      </div>
    )
  }

  return (
    <div
      className={`relative overflow-hidden rounded-lg cursor-pointer group ${className}`}
      style={{ width, height }}
      onClick={onClick}
    >
      {/* 隐藏的 canvas 用于生成缩略图 */}
      <canvas ref={canvasRef} className="hidden" />

      {/* 缩略图 */}
      {thumbnailUrl && (
        <img
          src={thumbnailUrl}
          alt="Video thumbnail"
          className="w-full h-full object-cover"
        />
      )}

      {/* 播放按钮覆盖层 */}
      {showPlayOverlay && (
        <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
          <div className="w-12 h-12 bg-white/90 rounded-full flex items-center justify-center">
            <Play size={24} className="text-black fill-current ml-1" />
          </div>
        </div>
      )}

      {/* 时长标签 */}
      {time > 0 && (
        <div className="absolute bottom-2 right-2 bg-black/70 text-white px-2 py-1 rounded text-xs">
          {Math.floor(time / 60)}:{(time % 60).toString().padStart(2, '0')}
        </div>
      )}
    </div>
  )
}
