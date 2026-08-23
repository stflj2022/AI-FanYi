# 自动化工程开发工作流

> 从设想到实现的完全自动化流程

## 功能特性

✅ **自动调用 Matt Skills**：集成 grill-with-docs、to-spec、to-tickets、implement、code-review
✅ **自动触发**：提交工程计划书/设想后自动启动并全程推进，无需用户逐阶段提醒
✅ **无人值守交接**：to-tickets 后自动启动无人值守系统，由 driver 自动实现直到完工自停
✅ **完工自停**：主线 + Web UI 工单全部完成后自动停止服务并发送一次终报
✅ **遵守 pi 规则**：提交前 code-review 审查两遍，无问题才提交
✅ **智能用户确认**：20分钟无响应暂停，1小时后重试，循环3次
✅ **无人值守集成**：与进度汇报系统无缝集成
✅ **自动恢复**：无人值守系统自动重启/恢复，崩溃可恢复
✅ **进度跟踪**：实时进度报告和状态文件

## 快速开始

### 1. 安装 Matt Skills

```bash
claude plugins install mattpocock-skills
```

### 2. 配置项目（skill 脚本自身 Phase 1-3 配置；无人值守系统无需此文件）

```bash
cp config.template.yaml .auto-engineering-config.yaml
# 编辑配置文件
nano .auto-engineering-config.yaml
```

### 3. 首次使用

提供计划书或设想即可，**系统会自动触发本工作流并一路推进到无人值守自动实现**（无需用户逐阶段提醒）：

```
这是我的工程计划书：...
```

或手动指定：

```
/skill:auto-engineering-workflow 我想做一个影视 AI 配音平台
```

## 工作流程

```
[1] 设计质询
    /grill-with-docs → 构建领域模型（设想需要；计划书跳过）

[2] 规范生成
    /to-spec → 生成规范文档

[3] 任务拆解
    /to-tickets → 拆解为 tickets

[4] 交接无人值守（自动接续，不等待确认）
    bash scripts/install-unattended.sh → 启动 driver + web-ui 驱动 + watchdog + 进度汇报

[5] 无人值守自动实现
    /implement → 实现 ticket（由 driver / web-ui-driver 逐张驱动）

[6] 代码审查（两遍）
    /code-review → 审查代码

[7] 提交推送
    git push → 推送到用户配置的目标仓库（origin/main 或其他）

[循环 4-6 直到完成] → 完工自停（completion-check → shutdown-unattended）+ 完成报告
```

## 用户确认策略

### 触发场景

- **下载失败**：自动尝试 10 次，失败后提示用户
- **关键决策**：架构分歧点、破坏性变更
- **失败恢复**：自动恢复失败 3 次后

### 提示机制

```
首次提示 → 等待20分钟 → 无响应暂停
    ↓
继续其他工作 1 小时 → 再次提示
    ↓
循环 3 次 → 标记为阻塞
```

### 非必要不提示

- ✅ 正常流程、自动修复、常规错误 → 不提示
- ⚠️ 需要人工干预、外部资源、关键决策 → 提示

## 配置文件

### 必需配置

```yaml
repository:
  owner: "your-username"  # 你的 GitHub 用户名
  repo: "your-repo"     # 你的 GitHub 仓库名
  branch: "main"         # 默认分支

git:
  target:
    remote: "origin"  # Git 远程仓库名称
    branch: "main"     # Git 分支名称

matt_skills:
  issue_tracker: "github"
```

### 可选配置

```yaml
code_review:
  max_review_attempts: 3

user_confirmation:
  first_response_timeout_minutes: 20
  max_retry_cycles: 3
```

## 状态文件

无人值守系统的状态由以下来源共同决定：

- **`docs/tickets/ticket-*.md`**：主线工单，状态行 `## 状态: done` 即完成
- **`.scratch/web-ui-tickets/`**：Web UI 工单，存在对应 `*-summary.md` 即完成
- **`scripts/completion-check.sh`**：唯一完工判据（`bash scripts/completion-check.sh && echo 已完工`）
- **日志**：`.claude/pi-driver.log`、`.claude/progress-report.log`、`.claude/web-ui-driver.log`

## 监控和调试

### 查看状态

```bash
systemctl --user list-timers aifanyi*
systemctl --user status aifanyi-driver.service --no-pager
```

### 查看日志

```bash
tail -f .claude/pi-driver.log
```

### 查看进度

```bash
bash scripts/view-reports.sh          # 查看最近汇报
bash scripts/progress-report.sh       # 手动触发一次汇报
```

## 故障排查

### 卡在某个阶段

```bash
# 查看无人值守系统状态
systemctl --user list-timers aifanyi*
systemctl --user status aifanyi-driver.service --no-pager

# 查看驱动日志
cat .claude/pi-driver.log | tail -100
```

### 用户确认超时

```bash
# 检查响应文件
ls -la /tmp/auto-engineering-response

# 手动创建响应文件
echo "yes" > /tmp/auto-engineering-response
```

### 代码审查失败

```bash
# 查看审查结果
/code-review HEAD~1

# 修复问题后继续
git add -A
git commit --amend
```

## 输出文件

| 文件/目录 | 说明 |
|------|------|
| `docs/specs/` | 规范文档 |
| `docs/adr/` | 架构决策 |
| `docs/tickets/` | 主线工单（无人值守系统读取） |
| `.scratch/web-ui-tickets/` | Web UI 工单集 |
| `.claude/pi-driver.log` | 驱动日志 |
| `.claude/progress-report.log` | 进度汇报日志 |
| `.claude/web-ui-driver.log` | Web UI 驱动日志 |
| `.claude/UNATTENDED_STOPPED` | 完工停止标记 |

> skill 脚本自身（Phase 1-3）还会生成 `.auto-engineering-status.yaml` / `.auto-engineering-log.md` / `.auto-engineering-checkpoints/` / `.auto-engineering-report.md` 作为自身跟踪（与无人值守系统状态无关）。

## 与无人值守系统集成 (v1.2.0 — systemd 版)

本 skill 负责设计/规范/任务拆解，**实现由无人值守系统自动完成**：

```bash
# 一键安装并启动无人值守系统（driver + web-ui 驱动 + watchdog + 进度汇报）
bash scripts/install-unattended.sh

# 查看状态
systemctl --user list-timers aifanyi*
systemctl --user status aifanyi-driver.service --no-pager

# 查看日志/汇报
tail -f .claude/pi-driver.log
bash scripts/view-reports.sh
```

**完工自停**：`docs/tickets` 与 `.scratch/web-ui-tickets` 全部完成时，`completion-check.sh` → `shutdown-unattended.sh` 自动停止全部服务并发送一次终报。

## 示例

### 示例 1：从设想开始

```
用户: 我想做一个影视 AI配音平台，能够自动将没有中文配音的影视剧生成中文配音

AI: [启动自动化工程工作流]
    [Phase 1] /grill-with-docs
        - 质询功能需求
        - 确定模块架构
        - 生成领域模型
    [Phase 2] /to-spec
        - 生成完整规范文档
    [Phase 3] /to-tickets
        - 拆解为 23 个 tickets
    [Phase 4-7] 自动实现
        - 实现 ticket 001-023
        - 每个经过 code-review
        - 推送到用户配置的目标仓库（如 origin/main）
    [完成] 生成完成报告
```

### 示例 2：从计划书开始

```
用户: < my-plan.md

AI: [跳过质询，直接生成规范]
    [Phase 2] /to-spec
    [Phase 3] /to-tickets
    [Phase 4-7] 自动实现...
```

## 注意事项

1. **首次使用前必须运行** `/setup-matt-pocock-skills`
2. **必须配置 GitHub SSH 密钥**
3. **必须确保有足够的 AI provider 配额**
4. **建议先在小项目上测试**
5. **所有代码提交必须经过 code-review**
6. **非必要不提示用户**，保持无人值守

## 依赖

- Matt Pocock Skills
- Claude Code / Codex
- Git
- GitHub SSH 密钥

## 许可

MIT License

---

**版本**: 1.2.0（与无人值守系统 v1.2.0 对齐）
**作者**: 基于 Matt Pocock Skills

**重要说明**：此 skill 会将生成的代码推送到用户在配置文件中指定的目标仓库，不是硬编码的特定仓库。每个项目可以配置不同的目标仓库。
