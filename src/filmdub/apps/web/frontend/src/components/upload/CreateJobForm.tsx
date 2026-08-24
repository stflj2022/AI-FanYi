/** 创建配音任务表单 - 上传完成后将媒体转成配音任务 */
import { useState, useEffect, useCallback } from 'react';
import { Play, Loader2 } from 'lucide-react';
import { projectAPI } from '../../services/projectAPI';
import jobAPI from '../../services/jobAPI';
import uploadAPI from '../../services/uploadAPI';

interface CreateJobFormProps {
  uploadId: string;
  filename: string;
  onCreated?: (jobId: string) => void;
}

export function CreateJobForm({ uploadId, filename, onCreated }: CreateJobFormProps) {
  const [projects, setProjects] = useState<Array<{ id: string; name: string }>>([]);
  const [jobName, setJobName] = useState(filename.replace(/\.[^.]+$/, ''));
  const [projectMode, setProjectMode] = useState<'select' | 'new'>('select');
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [newProjectName, setNewProjectName] = useState(filename.replace(/\.[^.]+$/, ''));
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // 加载项目列表
  const loadProjects = useCallback(async () => {
    setLoading(true);
    try {
      const data = await projectAPI.list({ page_size: 100 });
      const items = (data as any).items ?? [];
      setProjects(items.map((p: any) => ({ id: String(p.id), name: p.name || p.title || String(p.id) })));
      if (items.length > 0) {
        setSelectedProjectId(String(items[0].id));
      }
    } catch (e) {
      console.error('加载项目列表失败:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const handleCreate = async () => {
    if (!jobName.trim()) {
      setError('请输入任务名称');
      return;
    }
    setCreating(true);
    setError(null);
    setSuccess(null);
    try {
      // 1. 解析项目 ID：新建则先创建项目
      let projectId = selectedProjectId;
      if (projectMode === 'new') {
        if (!newProjectName.trim()) {
          setError('请输入新项目名称');
          setCreating(false);
          return;
        }
        const project = await projectAPI.create({ name: newProjectName.trim(), target_language: 'zh' });
        projectId = String((project as any).id);
      }
      if (!projectId) {
        setError('请选择或创建项目');
        setCreating(false);
        return;
      }

      // 2. 获取媒体资产 ID（作为任务输入）
      let mediaAssetId = uploadId;
      try {
        const metadata = await uploadAPI.getMediaMetadata(uploadId);
        if (metadata?.media_asset_id) {
          mediaAssetId = metadata.media_asset_id;
        }
      } catch {
        // 元数据获取失败时回退用上传会话 ID
      }

      // 3. 创建配音任务（M01 媒体输入模块）
      const job = await jobAPI.createJob({
        project_id: projectId,
        name: jobName.trim(),
        module_id: 'M01',
        input_artifacts: [mediaAssetId],
      });

      setSuccess(`配音任务已创建：${(job as any).name || jobName.trim()}`);
      onCreated?.(String((job as any).id));
    } catch (e: any) {
      setError(e?.message || '创建配音任务失败，请重试');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="mt-2 p-4 bg-blue-50/50 border border-blue-100 rounded-lg space-y-3">
      <div className="flex items-center space-x-2 text-sm font-medium text-gray-800">
        <Play className="w-4 h-4 text-blue-600" />
        <span>创建配音任务</span>
      </div>

      {/* 任务名称 */}
      <div>
        <label className="block text-xs text-gray-500 mb-1">任务名称</label>
        <input
          value={jobName}
          onChange={(e) => setJobName(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="输入任务名称"
        />
      </div>

      {/* 项目选择 */}
      <div>
        <label className="block text-xs text-gray-500 mb-1">项目</label>
        <div className="flex space-x-2">
          <button
            type="button"
            onClick={() => setProjectMode('select')}
            className={`px-3 py-1.5 rounded-md text-xs ${projectMode === 'select' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}
          >
            选择已有
          </button>
          <button
            type="button"
            onClick={() => setProjectMode('new')}
            className={`px-3 py-1.5 rounded-md text-xs ${projectMode === 'new' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}
          >
            + 新建项目
          </button>
        </div>

        {projectMode === 'select' ? (
          <select
            value={selectedProjectId}
            onChange={(e) => setSelectedProjectId(e.target.value)}
            className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-md text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {loading && <option value="">加载中...</option>}
            {!loading && projects.length === 0 && <option value="">暂无项目，请选择"新建项目"</option>}
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        ) : (
          <input
            value={newProjectName}
            onChange={(e) => setNewProjectName(e.target.value)}
            className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="输入新项目名称"
          />
        )}
      </div>

      {/* 错误/成功提示 */}
      {error && <div className="text-xs text-red-600">{error}</div>}
      {success && <div className="text-xs text-green-600">{success}</div>}

      {/* 提交 */}
      <button
        onClick={handleCreate}
        disabled={creating}
        className="w-full py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-md transition-colors flex items-center justify-center space-x-2"
      >
        {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
        <span>{creating ? '创建中...' : '开始配音'}</span>
      </button>
    </div>
  );
}
