# Ticket 013: Web 前端框架搭建

## 状态: done（第3轮复验通过：Vite+React+TS 项目可构建（npm run build 通过）、路由/布局/API 客户端/状态管理齐全；补齐 Workers/Settings 页面，清理重复死代码 pages/ 与 components/Layout，修复 apiClient 响应解包 bug 与全量 TS 错误）

## 优先级: 中

## 模块: Web Frontend

## 描述

搭建 Web 前端项目框架，配置开发环境、路由、状态管理和 UI 库。

## 任务清单

- [ ] 创建 `src/filmdub/apps/web/` 目录结构
- [ ] 初始化 React + TypeScript 项目 (Vite)
- [ ] 配置 `package.json` 和依赖
  - [ ] react, react-dom, react-router-dom
  - [ ] axios, zustand
  - [ ] antd
  - [ ] socket.io-client
  - [ ] recharts
- [ ] 配置 TypeScript (`tsconfig.json`)
- [ ] 配置 Vite (`vite.config.ts`)
- [ ] 配置 Tailwind CSS (`tailwind.config.js`)
- [ ] 创建 `src/main.tsx` - 应用入口
- [ ] 创建 `src/App.tsx` - 根组件
- [ ] 创建 `src/router/index.tsx` - 路由配置
- [ ] 创建 `src/services/api.ts` - API 客户端
  - [ ] axios 实例
  - [ ] 请求拦截器
  - [ ] 响应拦截器
  - [ ] 错误处理
- [ ] 创建 `src/store/` - 状态管理
  - [ ] `index.ts`
  - [ ] `projectStore.ts`
  - [ ] `uiStore.ts`
- [ ] 创建 `src/components/Layout/` - 布局组件
  - [ ] `Layout.tsx`
  - [ ] `Header.tsx`
  - [ ] `Sidebar.tsx`
- [ ] 配置开发服务器
- [ ] 配置构建脚本

## 依赖

- Ticket 003: REST API (后端需要先运行)

## 输出

- 完整的前端项目框架
- 路由配置
- API 客户端
- 状态管理
- 布局组件

## 验收标准

1. 项目可以正常启动 (`npm run dev`)
2. 路由正常工作
3. API 客户端可以连接后端
4. 状态管理正常
5. 布局组件渲染正确

## 参考 ADR

- specs/web-frontend.md
