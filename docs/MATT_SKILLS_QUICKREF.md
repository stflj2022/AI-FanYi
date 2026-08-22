# Matt 技能快速参考

## 🚀 常用命令速查

### 完整开发流程（大任务）
```bash
/grill-me           # 1. 质询设计
/to-spec            # 2. 生成规范
/to-tickets         # 3. 分解任务
/implement          # 4. 执行实现
/code-review main   # 5. 代码审查
```

### 快速流程（小任务）
```bash
/grill-me           # 1. 质询
/implement          # 2. 实现
/code-review HEAD~1 # 3. 审查
```

## 📋 技能说明

| 技能 | 用途 | 使用场景 |
|------|------|----------|
| `grill-me` | 激进质询 | 开工前澄清设计细节 |
| `grill-with-docs` | 质询+文档 | 同时生成 ADR 和术语表 |
| `to-spec` | 生成规范 | 大任务需要详细设计文档 |
| `to-tickets` | 分解任务 | 将规范拆分为可执行任务 |
| `implement` | 执行实现 | 自动处理任务依赖 |
| `code-review` | 代码审查 | 双轴审查（标准+规范） |

## 🎯 使用建议

### 什么时候用完整流程？
- ✅ 新增完整模块（M04-M14）
- ✅ 大型重构
- ✅ 跨多个模块的功能
- ✅ 需要详细设计文档

### 什么时候用快速流程？
- ✅ Bug 修复
- ✅ 简单功能增强
- ✅ 文档更新
- ✅ 小型重构

## 📊 Code-Review 双轴

**Standards 轴**：代码是否遵循项目编码规范？
**Spec 轴**：代码是否忠实实现原始规范？

## 📝 配置文件位置

```
CLAUDE.md                          # 项目级配置
docs/agents/
├── issue-tracker.md              # Issue Tracker 配置
├── triage-labels.md              # 分流标签配置
└── domain.md                     # 领域文档配置
CONTEXT.md                         # 领域模型
docs/MATT_SKILLS_GUIDE.md          # 详细使用指南
scripts/verify-matt-skills.sh      # 配置验证脚本
```

## 🔍 验证配置

```bash
cd /home/wu/桌面/AI-FanYi
bash scripts/verify-matt-skills.sh
```

## 💡 快速开始

```bash
cd /home/wu/桌面/AI-FanYi
/grill-me
```

就这么简单！🎉
