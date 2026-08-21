# Web 前端 - 用户界面

## 概述

Web 前端为影视AI配音平台提供用户界面，支持项目管理、作业监控、人物管理、音色配置等功能。

## 技术栈

- **框架**: React 18+
- **语言**: TypeScript
- **构建工具**: Vite
- **UI 库**: Ant Design / Material-UI
- **状态管理**: Zustand / Redux Toolkit
- **路由**: React Router v6
- **HTTP 客户端**: Axios
- **实时通信**: Socket.IO
- **图表**: Recharts / ECharts
- **样式**: Tailwind CSS / CSS Modules

## 核心页面

### 1. Dashboard (仪表盘)

**功能**:
- 系统概览统计
- 项目数量、作业状态
- Worker 状态
- 最近活动

**组件**:
- `StatsCard`: 统计卡片
- `ProjectChart`: 项目图表
- `WorkerList`: Worker 列表
- `RecentActivities`: 最近活动

### 2. Projects (项目管理)

**功能**:
- 项目列表和搜索
- 创建新项目
- 项目详情
- 项目配置

**组件**:
- `ProjectList`: 项目列表
- `ProjectCreate`: 创建项目表单
- `ProjectDetail`: 项目详情
- `ProjectSettings`: 项目设置

### 3. Jobs (作业管理)

**功能**:
- 作业列表和筛选
- 作业详情
- 作业日志
- 作业取消/重试

**组件**:
- `JobList`: 作业列表
- `JobDetail`: 作业详情
- `JobTimeline`: 作业时间轴
- `JobLogs`: 作业日志

### 4. Characters (人物管理)

**功能**:
- 人物列表
- 人物编辑
- 人物关系图
- 人工确认界面

**组件**:
- `CharacterList`: 人物列表
- `CharacterEdit`: 人物编辑
- `RelationshipGraph`: 关系图
- `CharacterConfirm`: 确认界面

### 5. Voice Profiles (音色管理)

**功能**:
- 音色列表
- 音色创建
- 音色预览
- 音色克隆

**组件**:
- `VoiceProfileList`: 音色列表
- `VoiceProfileCreate`: 创建音色
- `VoiceProfilePreview`: 音色预览
- `VoiceCloner`: 音色克隆器

### 6. Artifacts (Artifact 管理)

**功能**:
- Artifact 浏览
- Artifact 搜索
- Artifact 详情
- Artifact 下载

**组件**:
- `ArtifactList`: Artifact 列表
- `ArtifactDetail`: Artifact 详情
- `ArtifactSearch`: Artifact 搜索

### 7. Workers (Worker 监控)

**功能**:
- Worker 列表和状态
- Worker 详情
- Worker 资源使用
- Worker 日志

**组件**:
- `WorkerList`: Worker 列表
- `WorkerDetail`: Worker 详情
- `WorkerResources`: 资源监控
- `WorkerLogs`: Worker 日志

### 8. Workflows (工作流管理)

**功能**:
- 工作流列表
- 工作流编辑器 (DAG 可视化)
- 工作流执行

**组件**:
- `WorkflowList`: 工作流列表
- `WorkflowEditor`: DAG 编辑器
- `WorkflowExecutor`: 执行器

### 9. Settings (系统设置)

**功能**:
- 用户配置
- 系统配置
- 集成配置

**组件**:
- `UserSettings`: 用户设置
- `SystemSettings`: 系统设置
- `IntegrationSettings`: 集成设置

## 目录结构

```
src/filmdub/apps/web/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
├── public/
│   ├── favicon.ico
│   └── logo.svg
├── src/
│   ├── main.tsx              # 应用入口
│   ├── App.tsx               # 根组件
│   ├── index.css             # 全局样式
│   │
│   ├── router/               # 路由配置
│   │   └── index.tsx
│   │
│   ├── services/             # API 服务
│   │   ├── api.ts            # API 客户端
│   │   ├── project.ts        # 项目 API
│   │   ├── job.ts            # 作业 API
│   │   ├── worker.ts         # Worker API
│   │   ├── character.ts      # 人物 API
│   │   └── artifact.ts       # Artifact API
│   │
│   ├── store/                # 状态管理
│   │   ├── index.ts
│   │   ├── projectStore.ts
│   │   ├── jobStore.ts
│   │   └── uiStore.ts
│   │
│   ├── components/           # 公共组件
│   │   ├── Layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Layout.tsx
│   │   ├── UI/
│   │   │   ├── Button.tsx
│   │   │   ├── Modal.tsx
│   │   │   └── Table.tsx
│   │   └── Charts/
│   │       ├── LineChart.tsx
│   │       └── PieChart.tsx
│   │
│   ├── pages/                # 页面组件
│   │   ├── Dashboard/
│   │   │   └── index.tsx
│   │   ├── Projects/
│   │   │   ├── List.tsx
│   │   │   ├── Create.tsx
│   │   │   └── Detail.tsx
│   │   ├── Jobs/
│   │   │   ├── List.tsx
│   │   │   └── Detail.tsx
│   │   ├── Characters/
│   │   │   ├── List.tsx
│   │   │   └── Edit.tsx
│   │   ├── VoiceProfiles/
│   │   │   ├── List.tsx
│   │   │   └── Create.tsx
│   │   ├── Workers/
│   │   │   └── index.tsx
│   │   └── Settings/
│   │       └── index.tsx
│   │
│   ├── hooks/                # 自定义 Hooks
│   │   ├── useApi.ts
│   │   ├── useWebSocket.ts
│   │   └── usePolling.ts
│   │
│   ├── utils/                # 工具函数
│   │   ├── format.ts
│   │   ├── validation.ts
│   │   └── constants.ts
│   │
│   └── types/                # TypeScript 类型
│       ├── api.ts
│       ├── project.ts
│       ├── job.ts
│       └── common.ts
│
└── tests/                    # 测试
    ├── components/
    └── pages/
```

## 核心组件示例

### API 客户端

```typescript
// services/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  timeout: 30000,
});

// 请求拦截器
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      // 跳转到登录页
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

### WebSocket Hook

```typescript
// hooks/useWebSocket.ts
import { useEffect, useState } from 'react';

export function useWebSocket(url: string) {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<any[]>([]);

  useEffect(() => {
    const ws = new WebSocket(url);

    ws.onopen = () => {
      setConnected(true);
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      setMessages((prev) => [...prev, message]);
    };

    ws.onclose = () => {
      setConnected(false);
      console.log('WebSocket disconnected');
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return () => {
      ws.close();
    };
  }, [url]);

  return { connected, messages };
}
```

## 状态管理示例

```typescript
// store/projectStore.ts
import { create } from 'zustand';
import { api } from '../services/api';

interface Project {
  id: string;
  name: string;
  status: string;
  // ...
}

interface ProjectStore {
  projects: Project[];
  loading: boolean;
  error: string | null;
  fetchProjects: () => Promise<void>;
  createProject: (data: any) => Promise<void>;
}

export const useProjectStore = create<ProjectStore>((set) => ({
  projects: [],
  loading: false,
  error: null,

  fetchProjects: async () => {
    set({ loading: true, error: null });
    try {
      const response = await api.get('/projects');
      set({ projects: response.data, loading: false });
    } catch (error) {
      set({ error: 'Failed to fetch projects', loading: false });
    }
  },

  createProject: async (data) => {
    set({ loading: true, error: null });
    try {
      const response = await api.post('/projects', data);
      set((state) => ({
        projects: [...state.projects, response.data],
        loading: false
      }));
    } catch (error) {
      set({ error: 'Failed to create project', loading: false });
    }
  },
}));
```

## 配置

```json
// package.json
{
  "name": "filmdub-web",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.0",
    "zustand": "^4.4.0",
    "antd": "^5.12.0",
    "recharts": "^2.10.0",
    "socket.io-client": "^4.6.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "tailwindcss": "^3.3.0"
  }
}
```

## 实现优先级

### Phase 1: 基础框架 (高优先级)
1. 项目脚手架搭建
2. 路由配置
3. 布局组件
4. API 客户端

### Phase 2: 核心页面 (高优先级)
1. Dashboard
2. Projects (列表、创建、详情)
3. Jobs (列表、详情)

### Phase 3: 高级功能 (中优先级)
1. Characters 管理
2. Voice Profiles 管理
3. Workers 监控

### Phase 4: 实时功能 (中优先级)
1. WebSocket 集成
2. 实时更新
3. 通知系统

### Phase 5: 高级页面 (低优先级)
1. Workflows 编辑器
2. Settings
3. 高级分析图表

## 测试策略

1. **组件测试**: Vitest + React Testing Library
2. **E2E 测试**: Playwright
3. **可访问性测试**: axe-core
4. **性能测试**: Lighthouse

## 部署

- 开发环境: `npm run dev`
- 生产构建: `npm run build`
- 预览: `npm run preview`

静态文件部署到 Nginx 或 CDN。
