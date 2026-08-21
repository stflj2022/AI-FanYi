# 长期任务进度管理 - 快速指南

## 问题

- **上下文窗口限制**: AI 模型有固定上下文（1M tokens）
- **API 额度限制**: 智谱 API 每 5 小时重置一次
- **任务中断风险**: 长时间任务可能被中断

## 解决方案

使用内置的任务管理系统保存进度，随时恢复。

## 快速开始

### 1. 开始新任务

```bash
make task-start TASK_ID=implement-m01
```

### 2. 工作一段时间后保存进度

```bash
# 保存进度（当前阶段和说明）
make task-save PHASE=database-models MESSAGE="完成 SQLAlchemy 模型定义"

# 保存上下文摘要（更详细的描述）
make task-context SUMMARY="已完成:
- Project, Job, Artifact 表设计
- 关系定义
- 下一步: 创建 Repository 层"
```

### 3. 额度快用完时保存完整状态

```bash
make task-backup
```

这会:
- 检查当前额度状态
- 备份进度文件
- 提示更新上下文摘要

### 4. 等待额度重置

```bash
# 检查额度
make task-quota

# 如果需要，等待重置
# （手动检查重置时间，通常每5小时）
```

### 5. 恢复任务

```bash
make task-resume
```

这会显示:
- 任务 ID 和状态
- 当前阶段
- 上下文摘要
- 恢复指令（复制给 Claude）

## 完整工作流

```
开始任务 → 工作阶段 → 保存进度 → (额度不足?) → 等待重置 → 恢复任务 → 继续工作
            ↓                                               ↑
         保存上下文                                     检查额度
```

## 最佳实践

### 任务分解

将大任务分成小任务:

```
实现 M01 模块 (大任务)
├── 子任务 1: 数据库模型 (可独立完成)
├── 子任务 2: API 端点 (依赖子任务1)
├── 子任务 3: 业务逻辑 (依赖子任务1,2)
└── 子任务 4: 测试 (依赖前面所有)
```

每个子任务完成后保存进度。

### 保存时机

- ✅ 完成一个完整功能后
- ✅ 生成可验证的文件后
- ✅ 额度使用超过 80% 时
- ✅ 准备切换任务时

### 上下文摘要格式

```markdown
## 当前任务: 实现 M01 模块

### 已完成
- [x] 数据库模型设计
- [x] SQLAlchemy 模型定义
- [x] 基础 CRUD 操作

### 进行中
- [ ] API 端点实现 (50%)
  - [x] 项目创建端点
  - [ ] 项目更新端点
  - [ ] 项目删除端点

### 待完成
- [ ] 业务逻辑层
- [ ] 测试用例

### 技术细节
- 使用 FastAPI
- SQLAlchemy ORM
- Pydantic 验证

### 下一步
完成剩余的 CRUD 端点，然后添加业务逻辑
```

## Claude 恢复指令

恢复时使用以下格式的指令:

```
@Claude 从进度恢复任务

任务ID: implement-m01
当前阶段: api-endpoints
状态: 数据库模型已完成，API端点进行中

请根据 .claude/context-summary.md 中的详细上下文继续执行下一步。
```

## 进度文件位置

```
.claude/
├── task-progress.yaml      # 任务进度（自动生成）
├── context-summary.md      # 上下文摘要（手动编辑）
├── quota-usage.json        # 额度跟踪（自动生成）
└── scripts/                # 管理脚本
    ├── task-manager.sh
    ├── save-progress.sh
    ├── save-context.sh
    ├── resume.sh
    └── check-quota.py
```

## 何时保存

| 情况 | 操作 |
|------|------|
| 完成一个子模块 | `make task-save PHASE=module-name MESSAGE="完成模块X"` |
| 生成重要文件 | `make task-save` + git commit |
| 额度 < 20% | `make task-backup` + 等待重置 |
| 上下文快满 | `make task-context` 更新摘要 |
| 准备休息 | `make task-backup` |

## 检查清单

中断前检查:

- [ ] 进度已保存 (`make task-status`)
- [ ] 上下文摘要已更新
- [ ] 重要文件已提交 (`git commit`)
- [ ] 额度状态已检查 (`make task-quota`)

恢复后检查:

- [ ] 任务 ID 正确
- [ ] 当前阶段正确
- [ ] 上下文摘要清晰
- [ ] 下一步明确

## 故障排除

### 进度文件丢失

```bash
# 从备份恢复
cp .claude/task-progress.yaml.backup .claude/task-progress.yaml
```

### 无法恢复任务

```bash
# 查看所有进度文件
ls -la .claude/

# 手动创建进度
cat > .claude/task-progress.yaml << EOF
task_id: "manual-recovery"
status: "in_progress"
...
EOF
```

### 额度检查失败

```bash
# 手动检查额度
python3 .claude/scripts/check-quota.py
```

## 示例

### 完整任务周期

```bash
# 1. 开始任务
make task-start TASK_ID=implement-m01

# 2. 工作一会...（与 Claude 交互）
# ...生成代码...

# 3. 保存阶段成果
make task-save PHASE=database-models MESSAGE="完成表设计和ORM映射"

# 4. 继续工作...（与 Claude 交互）
# ...生成更多代码...

# 5. 检查额度
make task-quota
# 输出: 剩余 15% tokens，建议保存进度

# 6. 保存完整状态
make task-backup

# 7. 等待重置（或第二天继续）

# 8. 恢复任务
make task-resume

# 9. 继续工作...
```

## 集成到 Workflow

如果使用 Workflow 工具，进度会自动保存。

```javascript
// workflow 中自动保存
const result = await agent("实现 M01 模块...");

// 自动保存进度
saveProgress({
    phase: 'implementation',
    status: 'completed',
    context: result.summary
});
```
