import { CheckCircle2, Circle, Loader2, AlertCircle, XCircle } from 'lucide-react'

interface Stage {
  id: string
  name: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
}

interface JobStageDisplayProps {
  currentStage?: string
  previousStage?: string
  stages?: Stage[]
  size?: 'sm' | 'md' | 'lg'
}

export function JobStageDisplay({
  currentStage,
  previousStage,
  stages,
  size = 'md',
}: JobStageDisplayProps) {
  const sizeClasses = {
    sm: 'text-xs gap-1',
    md: 'text-sm gap-2',
    lg: 'text-base gap-3',
  }

  const iconSize = {
    sm: 14,
    md: 18,
    lg: 20,
  }

  // 如果提供了 stages 列表，使用它
  if (stages && stages.length > 0) {
    return (
      <div className={`flex items-center ${sizeClasses[size]} flex-wrap`}>
        {stages.map((stage, index) => (
          <div key={stage.id} className="flex items-center gap-2">
            {getStageIcon(stage.status, iconSize[size])}
            <span
              className={
                stage.status === 'in_progress'
                  ? 'font-medium text-blue-600'
                  : stage.status === 'completed'
                    ? 'text-gray-600'
                    : stage.status === 'failed'
                      ? 'text-red-600'
                      : 'text-gray-400'
              }
            >
              {stage.name}
            </span>
            {index < stages.length - 1 && (
              <span className="text-gray-300">→</span>
            )}
          </div>
        ))}
      </div>
    )
  }

  // 否则只显示当前阶段
  return (
    <div className={`flex items-center ${sizeClasses[size]}`}>
      {currentStage ? (
        <>
          <Loader2 className="animate-spin text-blue-500" size={iconSize[size]} />
          <span className="font-medium text-gray-700">
            {previousStage && (
              <span className="text-gray-400">{previousStage} → </span>
            )}
            {currentStage}
          </span>
        </>
      ) : (
        <span className="text-gray-400">等待开始...</span>
      )}
    </div>
  )
}

function getStageIcon(status: string, size: number) {
  switch (status) {
    case 'pending':
      return <Circle size={size} className="text-gray-300" />
    case 'in_progress':
      return <Loader2 size={size} className="animate-spin text-blue-500" />
    case 'completed':
      return <CheckCircle2 size={size} className="text-green-500" />
    case 'failed':
      return <XCircle size={size} className="text-red-500" />
    default:
      return null
  }
}
