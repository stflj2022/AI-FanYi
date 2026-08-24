/** 上传 API 服务 */
import apiClient from './api';

export type MediaType = 'video' | 'audio' | 'image';
export type UploadStatus = 'pending' | 'uploading' | 'ready' | 'failed';

export interface UploadResponse {
  id: string;
  status: UploadStatus;
  filename: string;
  file_size: number;
  mime_type: string;
  project_id?: string;
  media_type: MediaType;
  progress: number;
  created_at: string;
  updated_at: string;
}

export interface UploadProgressResponse {
  id: string;
  status: UploadStatus;
  progress: number;
  bytes_uploaded: number;
  total_bytes: number;
  speed_bytes_per_sec?: number;
  estimated_seconds_remaining?: number;
}

export interface StreamInfo {
  index: number;
  type: string;
  codec?: string;
  codec_long?: string;
  profile?: string;
  level?: string;
  width?: number;
  height?: number;
  frame_rate?: string;
  bit_rate?: number;
  channels?: number;
  sample_rate?: number;
  language?: string;
}

export interface MediaMetadataResponse {
  id: string;
  media_asset_id: string;
  filename: string;
  duration_seconds?: number;
  format?: string;
  streams: StreamInfo[];
  video_streams: StreamInfo[];
  audio_streams: StreamInfo[];
  subtitle_streams: StreamInfo[];
}

export interface UploadOptions {
  file: File;
  project_id?: string;
  media_type?: MediaType;
  onProgress?: (progress: number) => void;
  onSpeedChange?: (speed: number) => void;
  onEstimatedTimeChange?: (seconds: number) => void;
}

class UploadAPI {
  /**
   * 上传文件
   */
  async uploadFile(options: UploadOptions): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', options.file);
    formData.append('media_type', options.media_type || 'video');
    if (options.project_id) {
      formData.append('project_id', options.project_id);
    }

    // 使用 apiClient（axios 实例）以支持 onUploadProgress 进度回调；
    // FormData 由 axios 自动设置 multipart Content-Type（含 boundary）
    const response = await apiClient.post<UploadResponse>('/uploads', formData, {
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && options.onProgress) {
          options.onProgress((progressEvent.loaded / progressEvent.total) * 100);
        }
      },
    });

    return response.data;
  }

  /**
   * 获取上传进度
   */
  async getUploadProgress(uploadId: string): Promise<UploadProgressResponse> {
    const response = await apiClient.get<UploadProgressResponse>(`/uploads/${uploadId}`);
    return response.data;
  }

  /**
   * 获取媒体元数据
   */
  async getMediaMetadata(uploadId: string): Promise<MediaMetadataResponse> {
    const response = await apiClient.get<MediaMetadataResponse>(`/uploads/${uploadId}/metadata`);
    return response.data;
  }

  /**
   * 删除上传会话
   */
  async deleteUpload(uploadId: string): Promise<void> {
    await apiClient.delete(`/uploads/${uploadId}`);
  }
}

export default new UploadAPI();
