---
name: auto-engineering-workflow
description: "自动化工程开发工作流：从设想到实现的完整自动化流程，集成 Matt Skills 和无人值守系统"
disable-model-invocation: true
---

# 自动化工程开发工作流 Skill

## 功能概述

接受用户的设想或工程计划书，自动调用 Matt Pocock 的各个技能，生成最终计划书并实现，同时推送到 GitHub 仓库，遵守 pi 规则的提交审查流程。

## 核心流程

```
用户输入（设想/计划）
    ↓
[Phase 1] 设计质询
    ├─ /grill-with-docs 或 /grill-me
    └─ 构建领域模型，更新文档
    ↓
[Phase 2] 规范生成
    └─ /to-spec
        └─ 生成规范文档到 issue tracker
    ↓
[Phase 3] 任务拆解
    └─ /to-tickets
        └─ 拆解为带依赖关系的任务清单
    ↓
[Phase 4] 自动实现
    └─ /implement
        ├─ 使用 /tdd 测试驱动开发
        ├─ 按依赖顺序处理 tickets
        └─ 每个实现后触发 Phase 5
    ↓
[Phase 5] 代码审查（必须通过）
    ├─ 第一遍 code-review
    ├─ 如发现问题 → 修复 → 第二遍 code-review
    └─ 直到无问题
    ↓
[Phase 6] 提交推送
    ├─ 遵守 pi 规则
    ├─ git commit
    └─ git push to 用户配置的目标仓库（origin/main 或其他）
    ↓
[Phase 7] 循环继续
    └─ 回到 Phase 4 处理下一个 ticket
    ↓
完成 → 生成完成报告 → 通知用户
```

## 用户确认策略

### 需要用户确认的场景

1. **下载依赖失败**
   - 自动尝试下载模型/文件/依赖包
   - 最多尝试 10 次
   - 10 次后提示用户
   - 提供下载地址和手动安装步骤

2. **关键决策点**
   - 架构分歧点（2 个以上可行方案）
   - 破坏性变更
   - 外部服务依赖（API Key、第三方服务）

3. **失败恢复**
   - 自动恢复失败 3 次后
   - 需要用户介入

### 提示机制

```bash
[用户确认机制]
├─ 首次提示
│   └─ 立即通知
├─ 20分钟无回应
│   └─ 暂停提示，继续其他工作
├─ 工作1小时后
│   └─ 再次提示
└─ 如此循环
    └─ 直到用户回应
```

### 非必要不提示

- **不提示**：正常流程、自动修复、常规错误
- **提示**：需要人工干预、需要外部资源、关键决策

## 配置要求

### 项目配置

在项目根目录的 `.auto-engineering-config.yaml` 中配置：

```yaml
# GitHub 仓库（目标仓库，根据项目配置）
repository:
  owner: "your-username"  # GitHub 用户名
  repo: "your-repo"     # GitHub 仓库名
  branch: "main"         # 默认分支

# Git 配置（自动推送的目标）
git:
  target:
    remote: "origin"  # Git 远程仓库名称
    branch: "main"     # Git 分支名称

# Matt Skills 配置
matt_skills:
  issue_tracker: "github"  # github | linear | local
  triage_labels:
    - "feature"
    - "bug"
    - "refactor"
    - "docs"
  docs_path: "docs"
  adr_path: "docs/adr"

# 代码审查规则
code_review:
  pre_commit_required: true
  max_review_attempts: 3
  fail_on_any_finding: false
  auto_fix_minor_issues: true

# 用户确认配置
user_confirmation:
  download_retry_count: 10
  first_response_timeout_minutes: 20
  retry_interval_hours: 1
  max_retry_cycles: 3

# 无人值守集成
unattended:
  driver_log: ".unattended/logs/driver.log"
  progress_report_interval_minutes: 30
  notification_enabled: true
```

### 环境要求

- 已安装 Matt Skills (`/setup-matt-pocock-skills` 已运行)
- 已配置 git（SSH 密钥已设置）
- 已配置 GitHub access token（如需要）
- 项目已初始化（有 issue tracker）

## 执行步骤

### Step 1: 接收输入

分析用户输入，判断是：
- **设想**：模糊的想法、需求描述
- **计划书**：结构化的工程计划

```python
def analyze_input(user_input: str) -> dict:
    """分析用户输入类型"""
    if contains_structured_plan(user_input):
        return {"type": "plan", "ready_for_to_tickets": True}
    else:
        return {"type": "idea", "needs_grill": True}
```

### Step 2: 设计质询

**如果是设想**：
```bash
/grill-with-docs
```
- 质询设计细节
- 构建领域模型
- 更新 CONTEXT.md
- 生成 ADR 文档

**如果是计划书**：
- 直接进入规范生成

### Step 3: 生成规范

```bash
/to-spec
```
- 生成结构化规范文档
- 发布到 issue tracker
- 包含：
  - 功能描述
  - 技术方案
  - 验收标准
  - 依赖关系

### Step 4: 拆解任务

```bash
/to-tickets
```
- 将规范拆解为 tickets
- 标注依赖关系
- 确定优先级
- 发布到 issue tracker

### Step 5: 自动实现循环

```python
for ticket in sorted_tickets:
    # 5.1 检查依赖
    if not dependencies_met(ticket):
        continue

    # 5.2 实现功能
    /implement ${ticket}

    # 5.3 代码审查（必须通过）
    review_count = 0
    while True:
        /code-review HEAD~1

        if has_findings():
            if review_count >= max_review_attempts:
                notify_user("代码审查多次失败，需要人工介入")
                break
            fix_issues()
            review_count += 1
        else:
            break

    # 5.4 提交推送
    git commit -m "feat(${ticket.id}): ${ticket.title}"
    git push origin main

    # 5.5 更新 ticket 状态
    ticket.status = "done"

    # 5.6 进度报告
    send_progress_report()
```

### Step 6: 用户确认处理

```python
def handle_user_confirmation(task: dict) -> bool:
    """处理需要用户确认的任务"""

    # 尝试自动处理
    for attempt in range(10):
        if try_auto_handle(task):
            return True
        sleep(5)

    # 10 次失败后提示用户
    notify_user(
        message=task["message"],
        download_url=task["download_url"],
        manual_steps=task["manual_steps"]
    )

    # 等待用户响应
    for cycle in range(3):  # 最多3个循环
        response = wait_for_user_response(
            timeout_minutes=20
        )

        if response:
            return handle_user_response(response)

        # 20分钟无响应，暂停提示
        log("用户20分钟未响应，暂停提示，继续其他工作")

        # 继续其他工作
        continue_other_tasks()

        # 1小时后再次提示
        sleep(3600)  # 1小时
        notify_user(message=task["message"])

    # 3个循环后仍未响应
    log("用户多次未响应，标记任务为阻塞")
    mark_task_blocked(task)
    return False
```

### Step 7: 进度报告

集成无人值守系统的进度汇报：

```bash
# 每 30 分钟
/send-progress-report
```

报告内容：
- 当前阶段
- 已完成的 tickets
- 正在处理的 ticket
- 遇到的问题
- 代码审查结果
- Git 提交历史

### Step 8: 完成

生成完成报告：

```markdown
# 工程完成报告

## 项目信息
- 项目名称: {{project_name}}
- 完成时间: {{completion_time}}
- 总耗时: {{duration}}

## 统计
- 总 Tickets: {{total_tickets}}
- 已完成: {{completed_tickets}}
- 代码审查次数: {{review_count}}
- Git 提交数: {{commit_count}}

## 生成的文件
- 规范文档: {{spec_url}}
- Tickets: {{tickets_url}}
- 代码提交: {{commits_url}}

## 遗留问题
{{blocked_issues}}
```

## 错误处理

### 自动恢复

```python
def handle_error(error: Exception, context: dict) -> None:
    """错误处理和自动恢复"""

    error_type = classify_error(error)

    if error_type == "transient":
        # 临时错误：重试
        retry(context, max_attempts=3)

    elif error_type == "dependency":
        # 依赖问题：尝试自动安装
        try_install_dependency(error)

    elif error_type == "quota":
        # 配额问题：切换 provider
        switch_provider()

    elif error_type == "fatal":
        # 致命错误：通知用户
        notify_user(f"致命错误: {error}")
        mark_blocked(context["current_ticket"])

    log_error(error, context)
```

### Checkpoint 机制

每个阶段完成后保存 checkpoint：

```bash
/save-checkpoint phase1 "设计质询完成" "to-spec" "..."
/save-checkpoint phase2 "规范生成完成" "to-tickets" "..."
/save-checkpoint phase3 "任务拆解完成" "implement-ticket-001" "..."
```

崩溃后可以从 checkpoint 恢复：

```bash
/resume-from-checkpoint phase3
```

## 通知机制

### 桌面通知

```bash
notify-send \
    --app-name="Auto-Engineering" \
    --icon="dialog-information" \
    --urgency="normal" \
    --replace-id=2001 \
    --expire-time=0 \
    "🚀 自动化工程进度" \
    "当前阶段: {{phase}}\n完成: {{completed}}/{{total}}\n问题: {{issues}}"
```

### 状态文件

`.auto-engineering-status.yaml`:
```yaml
project_name: ""
current_phase: ""
total_tickets: 0
completed_tickets: 0
failed_tickets: []
last_checkpoint: ""
start_time: ""
estimated_completion: ""
```

## 与无人值守系统集成

### 作为 Driver 的一部分

将此 skill 集成到无人值守系统的主循环中：

```bash
# driver.sh 主循环
while [ $ALL_DONE = false ]; do
    # 检查是否有待处理的工程任务
    if has_pending_engineering_tasks; then
        /auto-engineering-workflow
    fi

    # 其他任务...
    sleep 300
done
```

### 使用 Orchestrator 管理

```bash
python orchestrator.py \
    --save "engineering" \
    --message "自动工程工作流" \
    --next "下一个任务" \
    --context "当前上下文"
```

## 使用示例

### 示例 1：从设想开始

```
用户: 我想做一个影视 AI 配音平台，能够自动将没有中文配音的影视剧生成中文配音

AI: [调用 /auto-engineering-workflow]
    [Phase 1] /grill-with-docs
        - 质询功能需求
        - 确定模块架构
        - 生成领域模型
    [Phase 2] /to-spec
        - 生成完整规范文档
    [Phase 3] /to-tickets
        - 拆解为 23 个 tickets
    [Phase 4-7] 自动实现循环
        - 实现 ticket 001-023
        - 每个经过 code-review
        - 推送到用户配置的目标仓库（如 origin/main）
    [完成] 生成完成报告
```

### 示例 2：从计划书开始

```
用户: 这是我的工程计划书...

AI: [调用 /auto-engineering-workflow]
    [跳过 Phase 1] 直接进入 /to-spec
    [Phase 2] /to-spec
    [Phase 3] /to-tickets
    [Phase 4-7] 自动实现...
```

## 触发方式

### 在 Claude Code 中

```
/auto-engineering-workflow
```

或使用自然语言触发：

```
"帮我实现这个想法：..."
"自动化开发这个项目：..."
"从计划开始构建这个系统：..."
```

### 在无人值守系统中

作为后台任务运行：

```bash
tmux new-session -d -s auto-engineering '/auto-engineering-workflow'
```

## 依赖的 Matt Skills

- `/grill-me` 或 `/grill-with-docs`
- `/to-spec`
- `/to-tickets`
- `/implement`
- `/tdd` (由 implement 内部调用)
- `/code-review`
- `/domain-modeling` (由 grill-with-docs 内部调用)

## 输出文件

```
.auto-engineering-config.yaml    # 配置文件
.auto-engineering-status.yaml    # 状态文件
.auto-engineering-log.md         # 执行日志
.auto-engineering-report.md      # 完成报告
docs/specs/                      # 生成的规范文档
docs/adr/                        # 生成的架构决策
```

## 注意事项

1. **首次使用前必须运行** `/setup-matt-pocock-skills`
2. **必须配置 GitHub SSH 密钥**
3. **必须确保有足够的 AI provider 配额**
4. **建议先在小项目上测试**
5. **非必要不提示用户**，保持真正的无人值守
6. **所有代码提交必须经过 code-review**，遵守 pi 规则

## 故障排查

### 卡在某个阶段

检查 checkpoint 和日志：
```bash
cat .auto-engineering-status.yaml
cat .auto-engineering-log.md | tail -50
```

### 用户确认超时

检查用户是否在线：
```bash
# 发送紧急通知
notify-send "紧急" "自动工程需要您的确认"
```

### 代码审查一直失败

检查代码质量规则：
```bash
/code-review HEAD~1
# 查看具体问题，修复后重新提交
```

---

**版本**: 1.0.0
**作者**: 基于 Matt Pocock Skills 和 Unattended Dev System

**注意**：此 skill 会将生成的代码推送到用户在配置文件中指定的目标仓库，不是硬编码的特定仓库。
