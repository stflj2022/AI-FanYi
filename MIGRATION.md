# 代码迁移说明

## 迁移概述

本次迁移将 `filmdub` 项目的已验证实现合并到 GitHub 仓库，建立统一的代码来源。

## 迁移内容

### 已实现模块

| 模块 | 名称 | 状态 | 测试日期 |
|------|------|------|----------|
| M01 | Project & Media Intake | ✅ 完成 | 2026-08-20 |
| M02 | Research Worker | ✅ 完成 | 2026-08-20 19:13 |
| M03 | Subtitle & Dialogue Acquisition | ✅ 代码完成 | 2026-08-20 |

### 目录结构

```
src/filmdub/
├── core/           # 核心配置、数据库、模型、存储
├── workers/        # 模块工作器
│   ├── media_intake/   # M01: 项目与媒体输入
│   ├── research/       # M02: 媒体研究
│   └── subtitle/       # M03: 字幕与对话获取
├── apps/           # 应用层
│   ├── api/           # FastAPI 后端
│   └── web/           # Web 前端（待实现）
├── tests/          # 测试套件
├── cli.py          # 命令行工具
└── __init__.py     # 模块导出
```

## 测试结果

### Module 01
- 测试视频: 绝命毒师 S01E01 (2.7GB, H.265, DTS 5.1, 1080p, 58:06)
- 处理时间: 78秒
- Project ID: proj_04a974754624
- 最终状态: READY_FOR_RESEARCH ✅

### Module 02
- TMDB API: ✅ 成功连接
- 获取数据: Breaking Bad (2008), TMDB ID: 1396
- 演员: 8位 (Bryan Cranston, Aaron Paul, Anna Gunn等)
- 角色: 8个 (Walter White, Jesse Pinkman, Skyler White等)
- 证据: 16条
- 处理时间: ~20秒
- 最终状态: READY_FOR_CHARACTERS ✅

## 下一步计划

1. **继续在统一仓库开发** M04+ 模块
2. **渐进接入 Layer 0 编排器** - 先保住现有成果，后续逐步集成
3. **完善测试覆盖** - 为已实现模块添加更多测试
4. **文档更新** - 更新设计文档与实现保持一致

## 项目数据

项目数据（数据库、媒体文件等）保留在本地，不进入 Git：

- `projects/*.sqlite` - 已被 .gitignore 排除
- `logs/` - 已被 .gitignore 排除
- `temp/` - 已被 .gitignore 排除

## 使用方法

### 本地开发

```bash
# 克隆仓库
git clone https://github.com/stflj2022/AI-FanYi.git
cd AI-FanYi

# 安装依赖
pip install -r requirements.txt

# 初始化环境
cp .env.example .env
# 编辑 .env 文件配置环境变量

# 运行 CLI
python src/filmdub/cli.py --help

# 启动 API
python src/filmdub/apps/api/main.py
```

### Docker 部署

```bash
# 构建 Docker 镜像
make build

# 启动服务
make up

# 查看日志
make logs
```

### 长期任务管理

```bash
# 开始新任务
make task-start TASK_ID=implement-m04

# 保存进度
make task-save PHASE=audio-analysis MESSAGE="完成 VAD 模块"

# 查看状态
make task-status

# 恢复任务
make task-resume

# 检查 API 额度
make task-quota

# 自动编排（无人值守）
make auto-start
make auto-resume
```

## 迁移日期

2026-08-21

## 迁移负责人

AI Assistant
