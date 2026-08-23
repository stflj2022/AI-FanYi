/** 任务 API 服务 */
import api from './api';

export type JobStatus =
  | 'pending'
  | 'scheduled'
  | 'running'
  | 'waiting'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'retrying';

export interface JobCreate {
  project_id: string;
  name: string;
  description?: string;
  workflow_id?: string;
  module_id?: string;
  input_artifacts?: string[];
  depends_on?: string[];
  config?: Record<string, any>;
}

export interface JobUpdate {
  name?: string;
  description?: string;
  config?: Record<string, any>;
}

export interface JobResponse {
  id: string;
  project_id: string;
  name: string;
  status: JobStatus;
  description?: string;

  // 执行信息
  module_id?: string;
  worker_id?: string;
  retry_count: number;
  max_retries: number;

  // 依赖
  depends_on?: string[];

  // 时间
  created_at: string;
  updated_at: string;
  scheduled_at?: string;
  started_at?: string;
  completed_at?: string;

  // 输入输出
  input_artifacts?: string[];
  output_artifacts?: string[];

  // 错误信息
  error_message?: string;
  error_stack?: string;
}

export interface JobListResponse {
  total: number;
  page: number;
  page_size: number;
  items: JobResponse[];
}

export interface JobActionResponse {
  id: string;
  status: JobStatus;
  message: string;
}

export interface JobQueryParams {
  project_id?: string;
  status?: JobStatus;
  module_id?: string;
  worker_id?: string;
  search?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

class JobAPI {
  /**
   * 创建任务
   */
  async createJob(jobData: JobCreate): Promise<JobResponse> {
    const response = await api.post<JobResponse>('/jobs', jobData);
    return response.data;
  }

  /**
   * 获取任务列表
   */
  async listJobs(params: JobQueryParams = {}): Promise<JobListResponse> {
    const response = await api.get<JobListResponse>('/jobs', { params });
    return response.data;
  }

  /**
   * 获取任务详情
   */
  async getJob(jobId: string): Promise<JobResponse> {
    const response = await api.get<JobResponse>(`/jobs/${jobId}`);
    return response.data;
  }

  /**
   * 更新任务
   */
  async updateJob(jobId: string, jobData: JobUpdate): Promise<JobResponse> {
    const response = await api.put<JobResponse>(`/jobs/${jobId}`, jobData);
    return response.data;
  }

  /**
   * 删除任务
   */
  async deleteJob(jobId: string): Promise<void> {
    await api.delete(`/jobs/${jobId}`);
  }

  /**
   * 暂停任务
   */
  async pauseJob(jobId: string, reason?: string): Promise<JobActionResponse> {
    const response = await api.post<JobActionResponse>(
      `/jobs/${jobId}/pause`,
      reason ? { reason } : undefined
    );
    return response.data;
  }

  /**
   * 恢复任务
   */
  async resumeJob(jobId: string, reason?: string): Promise<JobActionResponse> {
    const response = await api.post<JobActionResponse>(
      `/jobs/${jobId}/resume`,
      reason ? { reason } : undefined
    );
    return response.data;
  }

  /**
   * 取消任务
   */
  async cancelJob(jobId: string, reason?: string): Promise<JobActionResponse> {
    const response = await api.post<JobActionResponse>(
      `/jobs/${jobId}/cancel`,
      reason ? { reason } : undefined
    );
    return response.data;
  }

  /**
   * 重试任务
   */
  async retryJob(jobId: string, reason?: string): Promise<JobActionResponse> {
    const response = await api.post<JobActionResponse>(
      `/jobs/${jobId}/retry`,
      reason ? { reason } : undefined
    );
    return response.data;
  }
}

export default new JobAPI();
