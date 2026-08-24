/** 媒体信息显示组件 */
import { FileVideo, FileAudio, FileImage, Clock, Film, Music, Subtitles } from 'lucide-react';
import type { MediaMetadataResponse } from '../../services/uploadAPI';

interface MediaInfoProps {
  metadata: MediaMetadataResponse;
  className?: string;
}

export function MediaInfo({ metadata, className = '' }: MediaInfoProps) {
  const formatDuration = (seconds?: number): string => {
    if (!seconds) return '未知';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  const formatResolution = (width?: number, height?: number): string => {
    if (!width || !height) return '未知';
    return `${width}x${height}`;
  };

  const formatBitrate = (bitrate?: number): string => {
    if (!bitrate) return '未知';
    const mbps = bitrate / (1000 * 1000);
    return `${mbps.toFixed(2)} Mbps`;
  };

  const getMediaTypeIcon = () => {
    if (metadata.video_streams.length > 0) {
      return <FileVideo className="w-6 h-6 text-blue-500" />;
    } else if (metadata.audio_streams.length > 0) {
      return <FileAudio className="w-6 h-6 text-green-500" />;
    } else if (metadata.subtitle_streams.length > 0) {
      return <Subtitles className="w-6 h-6 text-purple-500" />;
    }
    return <Film className="w-6 h-6 text-gray-400" />;
  };

  return (
    <div className={`bg-white border border-gray-200 rounded-lg p-4 space-y-4 ${className}`}>
      {/* 标题栏 */}
      <div className="flex items-center space-x-3">
        {getMediaTypeIcon()}
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-gray-900 truncate">
            {metadata.filename}
          </h3>
          <p className="text-xs text-gray-500">
            ID: {metadata.media_asset_id}
          </p>
        </div>
      </div>

      {/* 基本信息 */}
      <div className="grid grid-cols-2 gap-4">
        {metadata.duration_seconds && (
          <div className="flex items-center space-x-2">
            <Clock className="w-4 h-4 text-gray-400" />
            <div>
              <p className="text-xs text-gray-500">时长</p>
              <p className="text-sm font-medium text-gray-900">
                {formatDuration(metadata.duration_seconds)}
              </p>
            </div>
          </div>
        )}

        {metadata.format && (
          <div className="flex items-center space-x-2">
            <Film className="w-4 h-4 text-gray-400" />
            <div>
              <p className="text-xs text-gray-500">格式</p>
              <p className="text-sm font-medium text-gray-900">
                {metadata.format.toUpperCase()}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* 视频流信息 */}
      {metadata.video_streams.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-gray-500 flex items-center space-x-1">
            <FileVideo className="w-3 h-3" />
            <span>视频流 ({metadata.video_streams.length})</span>
          </h4>
          {metadata.video_streams.map((stream, index) => (
            <div key={index} className="bg-gray-50 rounded p-3 space-y-2">
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-gray-500">编码:</span>{' '}
                  <span className="font-medium">{stream.codec || '未知'}</span>
                </div>
                <div>
                  <span className="text-gray-500">分辨率:</span>{' '}
                  <span className="font-medium">
                    {formatResolution(stream.width, stream.height)}
                  </span>
                </div>
                {stream.frame_rate && (
                  <div>
                    <span className="text-gray-500">帧率:</span>{' '}
                    <span className="font-medium">{stream.frame_rate}</span>
                  </div>
                )}
                {stream.bit_rate && (
                  <div>
                    <span className="text-gray-500">比特率:</span>{' '}
                    <span className="font-medium">{formatBitrate(stream.bit_rate)}</span>
                  </div>
                )}
                {stream.language && (
                  <div>
                    <span className="text-gray-500">语言:</span>{' '}
                    <span className="font-medium">{stream.language.toUpperCase()}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 音频流信息 */}
      {metadata.audio_streams.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-gray-500 flex items-center space-x-1">
            <Music className="w-3 h-3" />
            <span>音频流 ({metadata.audio_streams.length})</span>
          </h4>
          {metadata.audio_streams.map((stream, index) => (
            <div key={index} className="bg-gray-50 rounded p-3 space-y-2">
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-gray-500">编码:</span>{' '}
                  <span className="font-medium">{stream.codec || '未知'}</span>
                </div>
                {stream.channels && (
                  <div>
                    <span className="text-gray-500">声道:</span>{' '}
                    <span className="font-medium">{stream.channels}</span>
                  </div>
                )}
                {stream.sample_rate && (
                  <div>
                    <span className="text-gray-500">采样率:</span>{' '}
                    <span className="font-medium">
                      {(stream.sample_rate / 1000).toFixed(1)} kHz
                    </span>
                  </div>
                )}
                {stream.bit_rate && (
                  <div>
                    <span className="text-gray-500">比特率:</span>{' '}
                    <span className="font-medium">{formatBitrate(stream.bit_rate)}</span>
                  </div>
                )}
                {stream.language && (
                  <div>
                    <span className="text-gray-500">语言:</span>{' '}
                    <span className="font-medium">{stream.language.toUpperCase()}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 字幕流信息 */}
      {metadata.subtitle_streams.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-gray-500 flex items-center space-x-1">
            <Subtitles className="w-3 h-3" />
            <span>字幕流 ({metadata.subtitle_streams.length})</span>
          </h4>
          {metadata.subtitle_streams.map((stream, index) => (
            <div key={index} className="bg-gray-50 rounded p-3">
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-gray-500">编码:</span>{' '}
                  <span className="font-medium">{stream.codec || '未知'}</span>
                </div>
                {stream.language && (
                  <div>
                    <span className="text-gray-500">语言:</span>{' '}
                    <span className="font-medium">{stream.language.toUpperCase()}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
