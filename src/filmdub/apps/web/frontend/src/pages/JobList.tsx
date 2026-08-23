/** 任务列表页面 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { JobCard } from '../components/job/JobCard';
import { JobStatus, JobResponse, jobAPI } from '../services/jobAPI';
import {
  Filter,
  Search,
  Plus,
  RefreshCw,
  ChevronDown,
} from 'lucide-react';

export function JobList() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);

  // 筛选状态
  const [statusFilter, setStatusFilter] = useState<JobStatus | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // 加载任务列表
  const loadJobs = async () => {
    setLoading(true);
    try {
      const result = await jobAPI.listJobs({
        page,
        page_size: pageSize,
        status: statusFilter === 'all' ? undefined : statusFilter,
        search: searchQuery || undefined,
      });
      setJobs(result.items);
      setTotal(result.total);
    } catch (error) {
      console.error('Failed to load jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, [page, statusFilter, searchQuery]);

  // 任务操作
  const handlePause = async (jobId: string) => {
    try {
      await jobAPI.pauseJob(jobId);
      loadJobs();
    } catch (error) {
      console.error('Failed to pause job:', error);
    }
  };

  const handleResume = async (jobId: string) => {
    try {
      await jobAPI.resumeJob(jobId);
      loadJobs();
    } catch (error) {
      console.error('Failed to resume job:', error);
    }
  };

  const handleCancel = async (jobId: string) => {
    if (!confirm('确定要取消此任务吗？')) return;

    try {
      await jobAPI.cancelJob(jobId);
      loadJobs();
    } catch (error) {
      console.error('Failed to cancel job:', error);
    }
  };

  const handleRetry = async (jobId: string) => {
    try {
      await jobAPI.retryJob(jobId);
      loadJobs();
    } catch (error) {
      console.error('Failed to retry job:', error);
    }
  };

  const handleViewDetails = (jobId: string) => {
    navigate(`/jobs/${jobId}`);
  };

  const statusOptions: Array<{ value: JobStatus | 'all'; label: string }> = [
    { value: 'all', label: '全部' },
    { value: 'pending', label: '等待中' },
    { value: 'scheduled', label: '已调度' },
    { value: 'running', label: '运行中' },
    { value: 'waiting', label: '已暂停' },
    { value: 'completed', label: '已完成' },
    { value: 'failed', label: '失败' },
    { value: 'cancelled', label: '已取消' },
    { value: 'retrying', label: '重试中' },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 页面头部 */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">任务管理</h1>
              <p className="text-sm text-gray-500 mt-1">
                共 {total} 个任务
              </p>
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={loadJobs}
                className="flex items-center space-x-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                <span>刷新</span>
              </button>

              <button
                onClick={() => navigate('/jobs/create')}
                className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Plus className="w-4 h-4" />
                <span>创建任务</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 筛选和搜索栏 */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
          <div className="flex flex-col sm:flex-row gap-4">
            {/* 搜索 */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="搜索任务..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* 状态筛选 */}
            <div className="relative">
              <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as JobStatus | 'all')}
                className="pl-10 pr-10 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none cursor-pointer"
              >
                {statusOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
            </div>
          </div>
        </div>

        {/* 任务列表 */}
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-gray-300 border-t-blue-600"></div>
            <p className="mt-4 text-gray-500">加载中...</p>
          </div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-12 bg-white border border-gray-200 rounded-lg">
            <p className="text-gray-500">暂无任务</p>
          </div>
        ) : (
          <div className="grid gap-4">
            {jobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                onPause={() => handlePause(job.id)}
                onResume={() => handleResume(job.id)}
                onCancel={() => handleCancel(job.id)}
                onRetry={() => handleRetry(job.id)}
                onViewDetails={() => handleViewDetails(job.id)}
              />
            ))}
          </div>
        )}

        {/* 分页 */}
        {total > pageSize && (
          <div className="flex items-center justify-center space-x-2 mt-6">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              上一页
            </button>

            <span className="px-4 py-2 text-gray-700">
              第 {page} 页 / 共 {Math.ceil(total / pageSize)} 页
            </span>

            <button
              onClick={() => setPage((p) => Math.min(Math.ceil(total / pageSize), p + 1))}
              disabled={page >= Math.ceil(total / pageSize)}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              下一页
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
