/** 上传区域组件 - 支持拖拽上传 */
import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X, FileVideo, FileAudio, FileImage, AlertCircle } from 'lucide-react';
import uploadAPI from '../../services/uploadAPI';
import type { MediaType } from '../../services/uploadAPI';

interface UploadAreaProps {
  onUploadStart?: (file: File) => void;
  onUploadProgress?: (fileId: string, progress: number) => void;
  onUploadComplete?: (fileId: string, response: any) => void;
  onUploadError?: (fileId: string, error: Error) => void;
  projectId?: string;
  mediaType?: MediaType;
  maxFileSize?: number; // bytes
  acceptedFileTypes?: Record<string, string[]>;
  disabled?: boolean;
}

const DEFAULT_ACCEPTED_TYPES = {
  'video/*': ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.mpeg', '.mpg'],
  'audio/*': ['.mp3', '.wav', '.ogg', '.m4a'],
  'image/*': ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
};

const DEFAULT_MAX_SIZE = 10 * 1024 * 1024 * 1024; // 10GB

export function UploadArea({
  onUploadStart,
  onUploadProgress,
  onUploadComplete,
  onUploadError,
  projectId,
  mediaType = 'video',
  maxFileSize = DEFAULT_MAX_SIZE,
  acceptedFileTypes = DEFAULT_ACCEPTED_TYPES,
  disabled = false,
}: UploadAreaProps) {
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const getIconForType = (type: MediaType) => {
    switch (type) {
      case 'video':
        return <FileVideo className="w-12 h-12 text-blue-500" />;
      case 'audio':
        return <FileAudio className="w-12 h-12 text-green-500" />;
      case 'image':
        return <FileImage className="w-12 h-12 text-purple-500" />;
      default:
        return <Upload className="w-12 h-12 text-gray-400" />;
    }
  };

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (disabled) return;

      for (const file of acceptedFiles) {
        // 用 onUploadStart 返回的 taskId 作为 fileId，确保与 UploadManager 的 tasks key 一致
        // （否则进度/完成回调查不到对应任务，进度条永不更新）
        const fileId = onUploadStart?.(file) ?? crypto.randomUUID();

        try {
          const response = await uploadAPI.uploadFile({
            file,
            project_id: projectId,
            media_type: mediaType,
            onProgress: (progress) => {
              onUploadProgress?.(fileId, progress);
            },
          });

          onUploadComplete?.(fileId, response);
        } catch (error) {
          const err = error as Error;
          onUploadError?.(fileId, err);
        }
      }
    },
    [disabled, projectId, mediaType, onUploadStart, onUploadProgress, onUploadComplete, onUploadError]
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject, fileRejections } = useDropzone({
    onDrop,
    accept: acceptedFileTypes,
    maxSize: maxFileSize,
    disabled,
    multiple: true,
  });

  const hasRejectionErrors = fileRejections.length > 0;

  return (
    <div className="w-full">
      <div
        {...getRootProps()}
        className={`
          relative border-2 border-dashed rounded-lg p-8 transition-all cursor-pointer
          ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 bg-gray-50 hover:border-gray-400'}
          ${isDragReject ? 'border-red-500 bg-red-50' : ''}
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />

        <div className="flex flex-col items-center justify-center space-y-4">
          {getIconForType(mediaType)}

          <div className="text-center">
            <p className="text-lg font-medium text-gray-700">
              {isDragActive ? '释放文件以上传' : '拖拽文件到此处'}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              或点击选择文件
            </p>
          </div>

          <div className="text-xs text-gray-400 text-center">
            <p>最大文件大小: {formatFileSize(maxFileSize)}</p>
            <p>支持格式: {Object.values(acceptedFileTypes).flat().join(', ')}</p>
          </div>

          {hasRejectionErrors && (
            <div className="w-full max-w-md mt-4 space-y-2">
              {fileRejections.map((rejection, index) => (
                <div key={index} className="flex items-start space-x-2 p-3 bg-red-50 rounded-md">
                  <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-red-800 truncate">
                      {rejection.file.name}
                    </p>
                    {rejection.errors.map((error, i) => (
                      <p key={i} className="text-xs text-red-600">
                        {error.code === 'file-too-large'
                          ? `文件过大 (${formatFileSize(rejection.file.size)} > ${formatFileSize(maxFileSize)})`
                          : error.code === 'file-invalid-type'
                          ? '不支持的文件类型'
                          : error.message}
                      </p>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
