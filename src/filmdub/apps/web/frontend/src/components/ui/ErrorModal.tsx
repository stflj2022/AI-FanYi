import { XCircle, X, Copy, Check } from 'lucide-react'
import { useState } from 'react'

export interface ErrorDetail {
  error_code: string
  title: string
  message: string
  suggestion?: string
  type: 'recoverable' | 'retryable' | 'manual' | 'fatal'
  stack_trace?: string
  context?: Record<string, any>
}

interface ErrorModalProps {
  error: ErrorDetail
  isOpen: boolean
  onClose: () => void
  onRetry?: () => void
}

export function ErrorModal({ error, isOpen, onClose, onRetry }: ErrorModalProps) {
  const [copied, setCopied] = useState(false)

  if (!isOpen) return null

  const handleCopy = () => {
    const text = JSON.stringify(error, null, 2)
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const typeLabels = {
    recoverable: '可恢复',
    retryable: '可重试',
    manual: '需人工干预',
    fatal: '致命错误',
  }

  const typeColors = {
    recoverable: 'bg-yellow-100 text-yellow-800',
    retryable: 'bg-blue-100 text-blue-800',
    manual: 'bg-orange-100 text-orange-800',
    fatal: 'bg-red-100 text-red-800',
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* 头部 */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center gap-3">
            <XCircle className="w-6 h-6 text-red-600" />
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{error.title}</h2>
              <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${typeColors[error.type]}`}>
                {typeLabels[error.type]}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 内容 */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* 错误码 */}
          <div className="mb-4">
            <span className="text-sm text-gray-500">错误码：</span>
            <code className="px-2 py-1 bg-gray-100 rounded text-sm font-mono">
              {error.error_code}
            </code>
          </div>

          {/* 错误消息 */}
          <div className="mb-6">
            <p className="text-gray-900">{error.message}</p>
          </div>

          {/* 操作建议 */}
          {error.suggestion && (
            <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-900">
                <span className="font-semibold">💡 建议：</span>
                {error.suggestion}
              </p>
            </div>
          )}

          {/* 堆栈跟踪 */}
          {error.stack_trace && (
            <details className="mb-4">
              <summary className="cursor-pointer text-sm font-medium text-gray-700 hover:text-gray-900">
                查看详细堆栈跟踪
              </summary>
              <pre className="mt-2 p-4 bg-gray-900 text-gray-100 rounded-lg text-xs overflow-x-auto">
                {error.stack_trace}
              </pre>
            </details>
          )}

          {/* 上下文信息 */}
          {error.context && Object.keys(error.context).length > 0 && (
            <details className="mb-4">
              <summary className="cursor-pointer text-sm font-medium text-gray-700 hover:text-gray-900">
                查看上下文信息
              </summary>
              <pre className="mt-2 p-4 bg-gray-100 rounded text-xs overflow-x-auto">
                {JSON.stringify(error.context, null, 2)}
              </pre>
            </details>
          )}
        </div>

        {/* 底部 */}
        <div className="flex items-center justify-between p-6 border-t bg-gray-50">
          <button
            onClick={handleCopy}
            className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4" />
                已复制
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                复制错误信息
              </>
            )}
          </button>

          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              关闭
            </button>
            {error.type === 'retryable' && onRetry && (
              <button
                onClick={() => {
                  onRetry()
                  onClose()
                }}
                className="px-4 py-2 text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors"
              >
                重试
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
