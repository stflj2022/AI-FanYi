# 快速开始指南

## 🎉 迁移完成！

filmdub 的已验证实现（M01-M03）已成功迁移到 GitHub 仓库。现在这是一个统一的事实来源。

## 📦 在其他电脑上使用

### 1. 克隆仓库

```bash
git clone https://github.com/stflj2022/AI-FanYi.git
cd AI-FanYi
```

### 2. 初始化环境

```bash
# 使用 Makefile（推荐）
make init

# 或手动创建
mkdir -p artifacts uploads logs temp models projects
cp .env.example .env
# 编辑 .env 配置环境变量
```

### 3. 安装依赖

```bash
# 使用 pip
pip install -r requirements.txt

# 或使用 Make
make install
```

### 4. 运行

```bash
# 查看帮助
python src/filmdub/cli.py --help

# 创建项目
python src/filmdub/cli.py project create --title "作品名" --target-language zh-CN

# 导入媒体
python src/filmdub/cli.py media import <project_id> <视频路径>

# 启动研究（M02）
python src/filmdub/cli.py research start <project_id>

# 启动字幕处理（M03）
python src/filmdub/cli.py subtitle start <project_id>
```

## 🚀 Docker 部署

```bash
# 构建镜像
make build

# 启动服务
make up

# 查看日志
make logs
```

## 🤖 自动长期任务管理

### 启动自动编排器

```bash
make auto-start    # 启动自动任务编排器
make task-status   # 查看进度
make auto-resume   # 恢复任务
```

**注意**: `make auto-start` 是为 API 额度用尽后自动恢复设计的，每 5 分钟检查额度 → 超 80% 自动保存 → 等待重置 → 生成恢复指令。它与模块进度无关，不会检查项目状态或跳过已完成模块。

### 手动任务管理

```bash
make task-start TASK_ID=implement-m04      # 开始新任务
make task-save PHASE=vad MESSAGE="完成VAD" # 保存进度
make task-resume                           # 恢复任务
make task-quota                            # 检查额度
```

## 📊 已完成模块

| 模块 | 名称 | 状态 | 测试通过 |
|------|------|------|----------|
| M01 | Project & Media Intake | ✅ 完成 | ✅ 是 |
| M02 | Research Worker | ✅ 完成 | ✅ 是 |
| M03 | Subtitle & Dialogue Acquisition | ✅ 代码完成 | ⏳ 待测试 |

## 📁 项目结构

```
AI-FanYi/
├── src/filmdub/              # 源代码
│   ├── core/               # 核心配置、数据库、模型
│   ├── workers/            # 模块工作器 (M01-M03)
│   │   ├── media_intake/   # M01: 项目与媒体输入
│   │   ├── research/       # M02: 媒体研究
│   │   └── subtitle/       # M03: 字幕与对话
│   ├── apps/               # API 和 Web
│   ├── tests/              # 测试
│   └── cli.py              # 命令行工具
├── docs/
│   ├── adr/                # 24 ADR 架构设计文档
│   └── modules/            # 模块文档和测试报告
├── .claude/scripts/        # 自动编排器脚本
├── Makefile                # 便捷命令
├── docker-compose.yml      # Docker 编排
└── MIGRATION.md            # 迁移说明
```

## 🔄 推送代码到 GitHub

如果需要推送代码：

```bash
# 配置 Git 用户信息（首次）
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# 推送到 GitHub
git push origin main

# 或使用仓库脚本
./push-to-github.sh
```

## ⚠️ 重要提示

### 项目数据不会进入 Git

以下内容已被 .gitignore 排除：
- `projects/*.sqlite` - 项目数据库
- `logs/` - 日志文件
- `temp/` - 临时文件
- `*.db`, `*.sqlite` - 数据库文件

这意味着：
- ✅ 代码在 GitHub 上同步
- ✅ 项目数据保留在本地
- ✅ 每台电脑可以有各自的项目数据

### Module 01/02 已"跳过"

因为 M01/M02 代码已在仓库中，其他电脑克隆后：
- ✅ 不需要重新实现
- ✅ 可以直接使用 M01/M02
- ✅ 可以从 M03 开始开发新功能

## 📝 下一步

1. **在新电脑上克隆并测试**
2. **继续开发 M04+ 模块**
3. **渐进接入 Layer 0 编排器**（可选）
4. **完善测试覆盖**

## 🆘 遇到问题？

- 查看模块文档: `docs/modules/`
- 查看迁移说明: `MIGRATION.md`
- 查看架构设计: `docs/adr/`

---

**迁移日期**: 2026-08-21
**状态**: ✅ 完成
**下一步**: 在其他电脑上测试和使用
