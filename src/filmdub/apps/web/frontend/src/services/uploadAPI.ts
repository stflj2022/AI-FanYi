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
   * 上传文件（原生 XHR 实现：upload.onprogress 100% 触发上传进度）
   */
  async uploadFile(options: UploadOptions): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', options.file);
    formData.append('media_type', options.media_type || 'video');
    if (options.project_id) {
      formData.append('project_id', options.project_id);
    }

    const API_BASE = apiClient.defaults.baseURL || '/api/v1';

    return new Promise<UploadResponse>((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${API_BASE}/uploads`);

      const token = localStorage.getItem('access_token');
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      }

      // 上传进度：浏览器原生 upload 事件，可靠触发
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && options.onProgress) {
          options.onProgress(Math.round((e.loaded / e.total) * 100));
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText) as UploadResponse);
          } catch {
            reject(new Error('上传响应解析失败'));
          }
        } else {
          let detail = `上传失败 (${xhr.status})`;
          try {
            const parsed = JSON.parse(xhr.responseText);
            if (parsed?.detail) detail = typeof parsed.detail === 'string' ? parsed.detail : JSON.stringify(parsed.detail);
          } catch {
            // 忽略解析失败
          }
          reject(new Error(detail));
        }
      };
      xhr.onerror = () => reject(new Error('网络错误，上传失败'));

      // 不手动设置 Content-Type：浏览器对 FormData 自动生成带 boundary 的 multipart 头
      xhr.send(formData);
    });
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
