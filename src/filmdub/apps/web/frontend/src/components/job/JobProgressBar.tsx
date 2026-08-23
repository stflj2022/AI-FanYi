import { Progress } from '../ui/progress'

interface JobProgressBarProps {
  progress: number
  stage?: string
  message?: string
  size?: 'sm' | 'md' | 'lg'
  showStage?: boolean
  showMessage?: boolean
}

export function JobProgressBar({
  progress,
  stage,
  message,
  size = 'md',
  showStage = true,
  showMessage = true,
}: JobProgressBarProps) {
  const sizeClasses = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3',
  }

  const getColor = (progress: number) => {
    if (progress < 30) return 'bg-blue-500'
    if (progress < 70) return 'bg-yellow-500'
    return 'bg-green-500'
  }

  return (
    <div className="w-full space-y-2">
      {/* 进度条 */}
      <div className="flex items-center gap-3">
        <Progress
          value={progress}
          className={sizeClasses[size]}
        />
        <span className="text-sm font-medium text-gray-700 min-w-[3rem] text-right">
          {progress}%
        </span>
      </div>

      {/* 阶段和消息 */}
      {(showStage && stage) || (showMessage && message) ? (
        <div className="space-y-1">
          {showStage && stage && (
            <div className="text-xs font-medium text-gray-600">
              阶段: {stage}
            </div>
          )}
          {showMessage && message && (
            <div className="text-xs text-gray-500">
              {message}
            </div>
          )}
        </div>
      ) : null}
    </div>
  )
}
