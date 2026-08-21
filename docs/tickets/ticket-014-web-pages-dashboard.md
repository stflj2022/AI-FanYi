# Ticket 014: Web 前端 - Dashboard 和 Projects 页面

##状态: done

## 优先级: 中

## 模块: Web Frontend

## 描述

实现 Dashboard 仪表盘和 Projects 项目管理页面。

## 任务清单

### Dashboard 页面
- [ ] 创建 `src/pages/Dashboard/index.tsx` - Dashboard 页面
- [ ] 创建 `src/components/StatsCard.tsx` - 统计卡片
- [ ] 创建 `src/components/Charts/LineChart.tsx` - 折线图
- [ ] 创建 `src/components/Charts/PieChart.tsx` - 饼图
- [ ] 实现系统概览统计
- [ ] 实现项目数量图表
- [ ] 实现 Worker 状态图表
- [ ] 实现最近活动列表

### Projects 页面
- [ ] 创建 `src/pages/Projects/List.tsx` - 项目列表
  - [ ] 项目表格
  - [ ] 搜索和筛选
  - [ ] 分页
  - [ ] 状态标签
- [ ] 创建 `src/pages/Projects/Create.tsx` - 创建项目
  - [ ] 项目表单
  - [ ] 表单验证
  - [ ] 文件上传
- [ ] 创建 `src/pages/Projects/Detail.tsx` - 项目详情
  - [ ] 项目信息
  - [ ] 作业列表
  - [ ] 进度显示
  - [ ] Artifact 列表
- [ ] 创建 `src/services/project.ts` - 项目 API 服务
- [ ] 集成图表库 (Recharts)
- [ ] 实现实时更新 (WebSocket)

## 依赖

- Ticket 013: Web 前端框架

## 输出

- Dashboard 页面
- Projects 列表页面
- Projects 创建页面
- Projects 详情页面
- 项目 API 服务

## 验收标准

1. Dashboard 显示正确统计
2. 项目列表可以正常加载
3. 创建项目功能正常
4. 项目详情显示正确
5. 实时更新正常工作

## 参考 ADR

- specs/web-frontend.md
