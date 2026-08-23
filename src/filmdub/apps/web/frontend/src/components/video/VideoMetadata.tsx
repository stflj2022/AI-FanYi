import { Clock, FileText, Film, Gauge } from 'lucide-react'

interface VideoMetadataProps {
  duration?: number
  resolution?: string
  fileSize?: number
  format?: string
  bitrate?: number
  frameRate?: number
  codec?: string
}

export function VideoMetadata({
  duration,
  resolution,
  fileSize,
  format,
  bitrate,
  frameRate,
  codec,
}: VideoMetadataProps) {
  const formatDuration = (seconds?: number) => {
    if (!seconds) return '-'
    const hours = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)

    if (hours > 0) {
      return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return '-'
    const units = ['B', 'KB', 'MB', 'GB', 'TB']
    let size = bytes
    let unitIndex = 0

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024
      unitIndex++
    }

    return `${size.toFixed(2)} ${units[unitIndex]}`
  }

  const formatBitrate = (bps?: number) => {
    if (!bps) return '-'
    const mbps = bps / 1000000
    return `${mbps.toFixed(2)} Mbps`
  }

  const metadata = [
    {
      icon: <Clock size={18} />,
      label: '时长',
      value: formatDuration(duration),
    },
    {
      icon: <Film size={18} />,
      label: '分辨率',
      value: resolution || '-',
    },
    {
      icon: <FileText size={18} />,
      label: '文件大小',
      value: formatFileSize(fileSize),
    },
    {
      icon: <Gauge size={18} />,
      label: '码率',
      value: formatBitrate(bitrate),
    },
    {
      label: '格式',
      value: format || '-',
    },
    {
      label: '帧率',
      value: frameRate ? `${frameRate} fps` : '-',
    },
    {
      label: '编码',
      value: codec || '-',
    },
  ]

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">视频信息</h3>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {metadata.map((item, index) => (
          <div key={index} className="flex items-start gap-3">
            {item.icon && (
              <div className="flex-shrink-0 text-gray-400 mt-0.5">
                {item.icon}
              </div>
            )}
            <div className="min-w-0">
              <div className="text-sm text-gray-500">{item.label}</div>
              <div className="font-medium text-gray-900 truncate">{item.value}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
