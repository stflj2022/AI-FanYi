---
name: auto-engineering-workflow
description: "自动化工程开发工作流：当用户提交工程计划书或设想后，必须自动触发并一路推进到无人值守自动实现，无需用户逐阶段提醒。自动完成：设计质询/跳过→to-spec 规范→to-tickets 任务拆解→启动无人值守系统自动实现→双遍 code-review→提交推送→完工自停。当用户给出工程计划书、计划、设想、需求，或要求「自动开发」「自动化完成这个项目」「帮我实现这个想法」「从这个计划书开始」时使用。"
disable-model-invocation: false
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
[Phase 4] 自动实现（由无人值守系统驱动）
    └─ 无人值守系统 driver 逐张实现 ticket
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
全部完工 → 无人值守系统自动自停（completion-check.sh + shutdown-unattended.sh）
    → 生成完成报告 → 通知用户
```

### 自动接续铁律（必须遵守）

用户提交设想或工程计划书后，**必须自动启动并走完整个流程，禁止停在某一步等待用户提醒**：

1. **全程自动推进**：接到输入后直接进入 Step 1→4（质询/跳过→to-spec→to-tickets），各阶段之间不需要用户确认。
2. **to-tickets 完成后必须立即启动无人值守系统**（见 Step 5），把实现工作交接给 driver，**不要停下来问「是否开始自动实现？」**。
3. **正常流程不提示用户**；只有「需要人工干预、需要外部资源、关键决策」才提示（见下方确认策略）。
4. 若无人值守系统已在运行，直接确认其存活即可，不要重复安装。

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

在项目根目录的 `.auto-engineering-config.yaml` 中配置（**skill 脚本自身（Phase 1-3）的选项配置**；无人值守系统的安装/服务配置由 `scripts/install-unattended.sh` 提供，二者相互独立）：

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
  install_script: "scripts/install-unattended.sh"     # 一键安装并启动全部服务
  driver_service: "aifanyi-driver.service"            # 主驱动（docs/tickets 主线工单）
  web_ui_driver_service: "web-ui-driver.service"      # Web UI 工单驱动（.scratch/web-ui-tickets）
  watchdog_timer: "aifanyi-watchdog.timer"            # 每10分钟检查/恢复异常
  progress_report_timer: "aifanyi-progress-report.timer"  # 每30分钟进度汇报
  completion_check: "scripts/completion-check.sh"     # 唯一完工判据
  shutdown_script: "scripts/shutdown-unattended.sh"   # 完工自停（停/禁全部服务+终报）
  main_tickets_dir: "docs/tickets"                    # 主线工单目录
  web_ui_tickets_dir: ".scratch/web-ui-tickets"       # Web UI 工单目录
  driver_log: ".claude/pi-driver.log"
  web_ui_driver_log: ".claude/web-ui-driver.log"
  progress_report_log: ".claude/progress-report.log"
  progress_report_interval_minutes: 30
  watchdog_interval_minutes: 10
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

### Step 5: 交接无人值守系统（自动实现引擎）

**完成 Step 4 (to-tickets) 后，必须立即把实现工作交给无人值守系统，不要停下来等用户提醒。**

```bash
# 5.1 若尚未部署无人值守系统：安装并启动（v1.2.0：driver + web-ui 驱动 + watchdog + 进度汇报）
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
bash scripts/install-unattended.sh

# 5.2 若已部署（systemd 已存在）：确保全部服务在运行（含 web-ui-driver）
systemctl --user start aifanyi-driver.service
systemctl --user start web-ui-driver.service
systemctl --user start aifanyi-watchdog.timer
systemctl --user start aifanyi-progress-report.timer

# 5.3 验证无人值守系统已接管
systemctl --user status aifanyi-driver.service --no-pager | head -5
systemctl --user status web-ui-driver.service --no-pager | head -5
systemctl --user list-timers aifanyi* | grep -E "NEXT|LEFT"
```

无人值守系统的 `aifanyi-driver.service` 会读取 `docs/tickets/` 逐张自动实现（/implement → 双遍 code-review → 测试 → git commit+push → 进度汇报），`web-ui-driver.service` 会处理 `.scratch/web-ui-tickets/` 的 Web UI 工单；当两套工单全部完成时，`completion-check.sh` 判定完工，`shutdown-unattended.sh` 自动停止全部服务并发送一次终报。

> **禁止行为**：不要在 to-tickets 后询问「是否开始自动实现？」；正常流程直接启动无人值守，无需用户确认。

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

进度汇报由无人值守系统自动完成（`aifanyi-progress-report.timer` 每 30 分钟触发一次，见 `scripts/progress-report.sh`），无需当前会话手动发送：

```bash
# 查看最近汇报
bash scripts/view-reports.sh

# 手动触发一次汇报（如需）
bash scripts/progress-report.sh
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

无人值守系统的状态由以下来源共同决定：

- **`docs/tickets/ticket-*.md`**：主线工单，状态行 `## 状态: done` 即完成
- **`.scratch/web-ui-tickets/`**：Web UI 工单，存在对应 `*-summary.md` 即完成
- **`completion-check.sh`**：唯一完工判据（`bash scripts/completion-check.sh && echo 已完工`）
- **日志**：`.claude/pi-driver.log`、`.claude/progress-report.log`

## 与无人值守系统集成 (v1.2.0 — systemd 版)

本 skill 与无人值守系统的关系：**skill 负责设计/规范/任务拆解（Phase 1-3），无人值守系统负责自动实现（Phase 4-7）**。二者通过 `scripts/install-unattended.sh` 交接。

### 系统组件

| 组件 | 说明 |
|------|------|
| `aifanyi-driver.service` | 主驱动，读取 `docs/tickets/` 逐张实现（/implement → 双遍 code-review → 测试 → push） |
| `web-ui-driver.service` | Web UI 工单驱动，读取 `.scratch/web-ui-tickets/` 自动实现 |
| `aifanyi-watchdog.timer` | 每 10 分钟检查/恢复异常 |
| `aifanyi-progress-report.timer` | 每 30 分钟进度汇报 |
| `scripts/completion-check.sh` | 唯一完工判据（主线 + Web UI 两套工单全部 done） |
| `scripts/shutdown-unattended.sh` | 完工自停：停/禁全部服务 + 一次性终报 |

### 安装与启动

```bash
bash scripts/install-unattended.sh   # 一键安装并启动全部服务
```

### 查看状态

```bash
systemctl --user list-timers aifanyi*
systemctl --user status aifanyi-driver.service --no-pager
tail -f .claude/pi-driver.log
bash scripts/view-reports.sh   # 最近进度汇报
```

### 完工自停

当 `docs/tickets` 与 `.scratch/web-ui-tickets` 全部完成时，`completion-check.sh` 判定完工，由 `shutdown-unattended.sh` 停止并禁用全部服务并发送一次终报，无需人工干预。

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

AI: [自动触发 auto-engineering-workflow]
    [跳过 Phase 1] 直接进入 /to-spec
    [Phase 2] /to-spec
    [Phase 3] /to-tickets
    [Phase 4] 立即启动无人值守系统（install-unattended.sh），由 driver 自动实现
    [Phase 5-7] 无人值守循环：implement → 双遍 code-review → push → 进度汇报
    [完工自停] 生成完成报告，无需用户逐阶段提醒
```

## 触发方式

### 自动触发（本 skill 已允许模型自主调用）

当用户提交工程计划书、设想或需求时，模型**会自动加载本 skill 并全程执行**，无需用户手动输入命令。这是默认行为（`disable-model-invocation: false`）。

### 手动触发

```
/skill:auto-engineering-workflow
```

自然语言也会触发：

```
"帮我实现这个想法：..."
"自动化开发这个项目：..."
"从计划开始构建这个系统：..."
"这是我的工程计划书：..."
```

### 在无人值守系统中

无人值守系统以 systemd 服务方式运行（由 `scripts/install-unattended.sh` 安装），无需手动后台运行本 skill：

```bash
bash scripts/install-unattended.sh   # 安装并启动 driver + web-ui 驱动 + watchdog + 汇报
systemctl --user list-timers aifanyi*   # 查看定时器
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
docs/specs/                       # 生成的规范文档
docs/adr/                         # 生成的架构决策
docs/tickets/                     # 主线任务 tickets（无人值守系统读取）
.scratch/web-ui-tickets/          # Web UI 工单集（web-ui-driver 读取）
.claude/pi-driver.log             # 驱动日志
.claude/progress-report.log       # 进度汇报日志
.claude/web-ui-driver.log         # Web UI 驱动日志
.claude/UNATTENDED_STOPPED        # 完工停止标记
```

> skill 脚本自身（Phase 1-3）还会生成以下跟踪文件，与无人值守系统状态无关：
> `.auto-engineering-status.yaml`（状态）、`.auto-engineering-log.md`（日志）、`.auto-engineering-checkpoints/`（断点）、`.auto-engineering-report.md`（交接报告）

## 注意事项

1. **首次使用前必须运行** `/setup-matt-pocock-skills`
2. **必须配置 GitHub SSH 密钥**
3. **必须确保有足够的 AI provider 配额**
4. **建议先在小项目上测试**
5. **非必要不提示用户**，保持真正的无人值守
6. **所有代码提交必须经过 code-review**，遵守 pi 规则
7. **提交计划书后必须一路自动推进到启动无人值守**：不要停在 to-spec/to-tickets 等用户提醒；如无人值守已运行，先确认其存活，不要重复安装

## 故障排查

### 卡在某个阶段

检查无人值守系统状态和日志：
```bash
systemctl --user list-timers aifanyi*
systemctl --user status aifanyi-driver.service --no-pager
tail -50 .claude/pi-driver.log
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

**版本**: 1.2.0（与无人值守系统 v1.2.0 对齐）
**作者**: 基于 Matt Pocock Skills 和 Unattended Dev System

**注意**：此 skill 会将生成的代码推送到用户在配置文件中指定的目标仓库，不是硬编码的特定仓库。

## v1.2.0 变更记录

- 无人值守系统升级为 **systemd 版 v1.2.0**：`scripts/install-unattended.sh` + `aifanyi-driver.service` + `aifanyi-watchdog.timer` + `aifanyi-progress-report.timer` + `web-ui-driver.service`
- 新增 **完工自停**：`scripts/completion-check.sh` 判定完工 → `scripts/shutdown-unattended.sh` 停止全部服务并发送一次终报
- 新增 **Web UI 工单驱动**：`web-ui-driver.service` 自动实现 `.scratch/web-ui-tickets/` 下的 Web UI 工单
- 移除旧版 `driver.sh` / `orchestrator.py` / `.unattended/` 集成描述，统一为 systemd 版集成
