/** 文件上传页面 */
import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { UploadManager } from '../components/upload/UploadManager';
import { MediaType } from '../services/uploadAPI';
import { ArrowLeft, Video, Music, Image as ImageIcon } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export function Upload() {
  const { projectId } = useParams<{ projectId?: string }>();
  const [mediaType, setMediaType] = useState<MediaType>('video');
  const navigate = useNavigate();

  const handleUploadComplete = (taskId: string, response: any) => {
    console.log('Upload complete:', taskId, response);
    // 可以在这里添加上传完成后的处理逻辑
    // 例如：显示通知、跳转到媒体详情页等
  };

  const mediaTypes: Array<{ value: MediaType; label: string; icon: React.ReactNode }> = [
    { value: 'video', label: '视频', icon: <Video className="w-5 h-5" /> },
    { value: 'audio', label: '音频', icon: <Music className="w-5 h-5" /> },
    { value: 'image', label: '图片', icon: <ImageIcon className="w-5 h-5" /> },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 页面头部 */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => navigate(-1)}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
              title="返回"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>

            <div className="flex-1">
              <h1 className="text-2xl font-bold text-gray-900">文件上传</h1>
              <p className="text-sm text-gray-500 mt-1">
                {projectId ? `上传到项目 ${projectId}` : '上传文件'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* 主内容区 */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* 左侧：上传区域 */}
          <div className="lg:col-span-2 space-y-6">
            {/* 媒体类型选择 */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">选择媒体类型</h2>
              <div className="grid grid-cols-3 gap-4">
                {mediaTypes.map((type) => (
                  <button
                    key={type.value}
                    onClick={() => setMediaType(type.value)}
                    className={`
                      flex flex-col items-center justify-center p-4 border-2 rounded-lg transition-all
                      ${
                        mediaType === type.value
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }
                    `}
                  >
                    <div className={mediaType === type.value ? 'text-blue-500' : 'text-gray-400'}>
                      {type.icon}
                    </div>
                    <span
                      className={`mt-2 text-sm font-medium ${
                        mediaType === type.value ? 'text-blue-700' : 'text-gray-700'
                      }`}
                    >
                      {type.label}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* 上传管理器 */}
            <UploadManager
              projectId={projectId}
              mediaType={mediaType}
              onUploadComplete={handleUploadComplete}
            />
          </div>

          {/* 右侧：提示信息 */}
          <div className="space-y-6">
            {/* 上传提示 */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">上传提示</h3>
              <ul className="space-y-3 text-sm text-gray-600">
                <li className="flex items-start space-x-2">
                  <span className="text-green-500 mt-0.5">✓</span>
                  <span>支持拖拽上传多个文件</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-green-500 mt-0.5">✓</span>
                  <span>最大文件大小: 10GB</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-green-500 mt-0.5">✓</span>
                  <span>上传时自动提取媒体元数据</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-green-500 mt-0.5">✓</span>
                  <span>支持视频、音频、图片格式</span>
                </li>
              </ul>
            </div>

            {/* 支持的格式 */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">支持的格式</h3>

              {mediaType === 'video' && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">视频</h4>
                  <p className="text-xs text-gray-500 mb-4">
                    MP4, MOV, AVI, MKV, WebM, MPEG, MPG
                  </p>
                </div>
              )}

              {mediaType === 'audio' && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">音频</h4>
                  <p className="text-xs text-gray-500 mb-4">MP3, WAV, OGG, M4A</p>
                </div>
              )}

              {mediaType === 'image' && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">图片</h4>
                  <p className="text-xs text-gray-500 mb-4">JPG, JPEG, PNG, GIF, WebP</p>
                </div>
              )}

              <div className="text-xs text-gray-400">
                * 更多格式正在添加中
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
