#!/bin/bash
# 自动化工程开发工作流 - 主驱动脚本（v1.2.0 — 交接 systemd 版无人值守系统）
# 职责：Phase 1-3（质询/规范/任务拆解）→ Phase 4 交接无人值守系统（install-unattended.sh）
#       实现/代码审查/提交推送/进度汇报/完工自停均由无人值守系统自动完成。

set -e

# 配置
PROJECT_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
CONFIG_FILE="$PROJECT_ROOT/.auto-engineering-config.yaml"
STATUS_FILE="$PROJECT_ROOT/.auto-engineering-status.yaml"
LOG_FILE="$PROJECT_ROOT/.auto-engineering-log.md"
CHECKPOINT_DIR="$PROJECT_ROOT/.auto-engineering-checkpoints"

# Git 目标仓库（从配置文件读取，默认为 origin/main）
GIT_TARGET_REMOTE="origin"
GIT_TARGET_BRANCH="main"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 初始化
init() {
    mkdir -p "$CHECKPOINT_DIR"

    if [ ! -f "$CONFIG_FILE" ]; then
        log "ERROR" "配置文件不存在: $CONFIG_FILE"
        log "INFO" "请先运行 /setup-matt-pocock-skills 并创建配置文件"
        exit 1
    fi

    if [ ! -f "$STATUS_FILE" ]; then
        create_status_file
    fi

    # 从配置文件读取 Git 目标仓库设置
    GIT_TARGET_REMOTE=$(yq '.git.target.remote' "$CONFIG_FILE" 2>/dev/null || echo "origin")
    GIT_TARGET_BRANCH=$(yq '.git.target.branch' "$CONFIG_FILE" 2>/dev/null || echo "main")

    log "INFO" "自动化工程工作流启动"
    log "INFO" "项目根目录: $PROJECT_ROOT"
    log "INFO" "目标仓库: $GIT_TARGET_REMOTE/$GIT_TARGET_BRANCH"
}

# 创建状态文件
create_status_file() {
    cat > "$STATUS_FILE" << EOF
project_name: ""
current_phase: ""
total_tickets: 0
completed_tickets: 0
failed_tickets: ""  # 注意：YAML 数组在 shell source 时会有问题
last_checkpoint: ""
start_time: $(date +"%Y-%m-%dT%H:%M:%S%z")  # POSIX 兼容
estimated_completion: ""
EOF
}

# 日志函数
log() {
    local level="$1"
    shift
    local message="$*"  # POSIX 兼容：使用 $* 合并参数
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")  # POSIX 兼容
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

# 保存 checkpoint
save_checkpoint() {
    local phase="$1"
    local message="$2"
    local next="$3"
    local context="$4"

    local checkpoint_file="$CHECKPOINT_DIR/${phase}.yaml"
    cat > "$checkpoint_file" << EOF
phase: $phase
message: $message
next: $next
timestamp: $(date +"%Y-%m-%dT%H:%M:%S%z")  # POSIX 兼容
context: |
  $context
EOF

    # 更新状态文件
    yq -i ".last_checkpoint = \"$phase\"" "$STATUS_FILE"

    log "INFO" "Checkpoint 保存: $phase"
}

# 加载 checkpoint
load_checkpoint() {
    local phase="$1"
    local checkpoint_file="$CHECKPOINT_DIR/${phase}.yaml"

    if [ ! -f "$checkpoint_file" ]; then
        log "ERROR" "Checkpoint 不存在: $phase"
        return 1
    fi

    source "$checkpoint_file"
    log "INFO" "从 checkpoint 恢复: $phase"
}

# 发送通知
send_notification() {
    local title="$1"
    local message="$2"
    local urgency="${3:-normal}"

    if command -v notify-send >/dev/null 2>&1; then
        notify-send \
            --app-name="Auto-Engineering" \
            --icon="dialog-information" \
            --urgency="$urgency" \
            --replace-id=2001 \
            --expire-time=0 \
            "$title" \
            "$message"
    fi

    log "NOTIFY" "$title: $message"
}

# 等待用户响应
wait_for_user_response() {
    local timeout_minutes="$1"
    local timeout_seconds=$((timeout_minutes * 60))

    log "INFO" "等待用户响应（${timeout_minutes}分钟）..."

    # 在实际实现中，这里需要集成到用户交互界面
    # 对于无人值守模式，可以检查特定的文件或信号
    local response_file="/tmp/auto-engineering-response"

    local i=1
    while [ $i -le $timeout_seconds ]; do
        if [ -f "$response_file" ]; then
            local response=$(cat "$response_file")
            rm -f "$response_file"
            echo "$response"
            return 0
        fi
        sleep 1
        i=$((i + 1))
    done

    return 1
}

# 处理需要用户确认的任务
handle_user_confirmation() {
    local task_type="$1"
    local message="$2"
    local download_url="$3"
    local manual_steps="$4"

    log "INFO" "需要用户确认: $task_type"

    # 尝试自动处理（针对下载任务）
    if [ "$task_type" = "download" ]; then
        local attempt=1
        while [ $attempt -le 10 ]; do
            log "INFO" "自动下载尝试 $attempt/10"
            if attempt_download "$download_url"; then
                log "INFO" "自动下载成功"
                return 0
            fi
            sleep 5
            attempt=$((attempt + 1))
        done
    fi

    # 10 次失败后提示用户
    send_notification "⚠️ 需要用户确认" "$message\n\n下载地址: $download_url\n\n手动步骤:\n$manual_steps" "critical"

    # 等待用户响应循环（POSIX 兼容）
    local cycle=1
    while [ $cycle -le 3 ]; do
        local response=$(wait_for_user_response 20)

        if [ -n "$response" ]; then
            log "INFO" "收到用户响应: $response"
            return 0
        fi

        # 20分钟无响应
        log "INFO" "用户20分钟未响应，暂停提示，继续其他工作"
        continue_other_tasks

        # 1小时后再次提示
        log "INFO" "等待1小时后再次提示"
        sleep 3600
        send_notification "⚠️ 仍需用户确认" "$message" "critical"
        cycle=$((cycle + 1))
    done

    # 3个循环后仍未响应
    log "ERROR" "用户多次未响应，标记任务为阻塞"
    return 1
}

# 尝试下载
attempt_download() {
    local url="$1"
    # 实现具体的下载逻辑
    log "INFO" "尝试下载: $url"
    # 返回 0 表示成功，1 表示失败
    return 1
}

# 继续其他工作
continue_other_tasks() {
    log "INFO" "继续其他工作..."
    # 可以在这里实现其他任务的处理逻辑
}

# Phase 1: 设计质询
phase1_grill() {
    log "INFO" "=== Phase 1: 设计质询 ==="

    # 检查是否需要质询
    if is_idea_input; then
        log "INFO" "检测到设想输入，启动 /grill-with-docs"
        # 调用 Matt Skill
        /grill-with-docs
    else
        log "INFO" "检测到计划书输入，跳过质询"
    fi

    save_checkpoint "phase1" "设计质询完成" "phase2" "领域模型已构建"
}

# Phase 2: 规范生成
phase2_to_spec() {
    log "INFO" "=== Phase 2: 规范生成 ==="

    # 调用 Matt Skill
    /to-spec

    save_checkpoint "phase2" "规范生成完成" "phase3" "规范文档已发布到 issue tracker"
}

# Phase 3: 任务拆解
phase3_to_tickets() {
    log "INFO" "=== Phase 3: 任务拆解 ==="

    # 调用 Matt Skill
    /to-tickets

    # 统计 tickets
    local total_tickets=$(count_tickets)
    yq -i ".total_tickets = $total_tickets" "$STATUS_FILE"

    save_checkpoint "phase3" "任务拆解完成" "phase4" "共 $total_tickets 个 tickets"
}

# Phase 4: 交接无人值守系统（v1.2.0 — systemd 版）
phase4_handoff_unattended() {
    log "INFO" "=== Phase 4: 交接无人值守系统 ==="

    local project_root="$(git rev-parse --show-toplevel 2>/dev/null || echo "$PROJECT_ROOT")"

    # 4.1 若无人值守系统已部署且 driver 在运行：确认存活即可，不重复安装
    if systemctl --user is-active aifanyi-driver.service >/dev/null 2>&1; then
        log "INFO" "无人值守系统已在运行，确认存活（不重复安装）"
        systemctl --user status aifanyi-driver.service --no-pager | head -5
        systemctl --user list-timers aifanyi* | grep -E "NEXT|LEFT"
        save_checkpoint "phase4" "无人值守系统确认存活，实现已交接" "phase4" "由 driver/web-ui-driver 自动实现"
        return 0
    fi

    # 4.2 未部署：安装并启动（v1.2.0：driver + web-ui 驱动 + watchdog + 进度汇报）
    if [ -f "$project_root/scripts/install-unattended.sh" ]; then
        log "INFO" "启动无人值守系统: scripts/install-unattended.sh"
        (cd "$project_root" && bash scripts/install-unattended.sh)
    else
        log "ERROR" "未找到 scripts/install-unattended.sh —— 请先将无人值守系统（scripts/ + systemd/）放入项目根目录"
        send_notification "⚠️ 无人值守系统未部署" "项目缺少 scripts/install-unattended.sh，请先部署 v1.2.0 无人值守系统" "critical"
        return 1
    fi

    # 4.3 验证接管
    systemctl --user status aifanyi-driver.service --no-pager | head -5
    systemctl --user status web-ui-driver.service --no-pager | head -5
    systemctl --user list-timers aifanyi* | grep -E "NEXT|LEFT"

    save_checkpoint "phase4" "无人值守系统已启动，实现已交接" "phase4" "由 driver/web-ui-driver 自动实现"
    send_notification "🤖 无人值守系统已接管" "tickets 已交接，driver/web-ui-driver 自动实现，完工自停" "normal"
    log "INFO" "无人值守系统已接管实现工作"
}

# 生成交接完成报告
# （最终完工报告由无人值守系统在 completion-check.sh 判定完工后生成）
generate_completion_report() {
    log "INFO" "生成交接完成报告..."

    local report_file="$PROJECT_ROOT/.auto-engineering-report.md"
    local total=$(yq '.total_tickets' "$STATUS_FILE")
    local start_time=$(yq '.start_time' "$STATUS_FILE")
    local end_time=$(date +"%Y-%m-%dT%H:%M:%S%z")  # POSIX 兼容

    cat > "$report_file" << EOF
# 工程交接完成报告

## 项目信息
- 项目名称: $(yq '.project_name' "$STATUS_FILE")
- 交接时间: $end_time

## 统计
- 总 Tickets: $total
- 无人值守系统: systemd 版 v1.2.0
- 完工判据: scripts/completion-check.sh（主线 docs/tickets + Web UI .scratch/web-ui-tickets）
- 完工自停: scripts/shutdown-unattended.sh（停/禁全部服务 + 一次终报）

## 生成的文档
- 规范文档: docs/specs/
- Tickets: docs/tickets/ + .scratch/web-ui-tickets/
- 驱动日志: .claude/pi-driver.log

## 后续
- 实现/代码审查/提交推送/进度汇报/完工自停由无人值守系统自动完成

---

**自动化工程已交接无人值守系统**
EOF

    log "INFO" "交接报告已生成: $report_file"
}

# 主函数
main() {
    init

    # 加载状态
    local last_checkpoint=$(yq '.last_checkpoint' "$STATUS_FILE")

    if [ -n "$last_checkpoint" ]; then
        log "INFO" "从 checkpoint 恢复: $last_checkpoint"
    fi

    # Phase 1: 设计质询
    if [ "$last_checkpoint" != "phase1" ] && [ "$last_checkpoint" != "phase2" ] && [ "$last_checkpoint" != "phase3" ]; then
        yq -i ".current_phase = \"phase1\"" "$STATUS_FILE"
        phase1_grill
    fi

    # Phase 2: 规范生成
    if [ "$last_checkpoint" != "phase2" ] && [ "$last_checkpoint" != "phase3" ]; then
        yq -i ".current_phase = \"phase2\"" "$STATUS_FILE"
        phase2_to_spec
    fi

    # Phase 3: 任务拆解
    if [ "$last_checkpoint" != "phase3" ]; then
        yq -i ".current_phase = \"phase3\"" "$STATUS_FILE"
        phase3_to_tickets
    fi

    # Phase 4-7: 交接无人值守系统（实现循环由无人值守系统完成）
    yq -i ".current_phase = \"phase4\"" "$STATUS_FILE"
    phase4_handoff_unattended

    # 完成（交接完成报告）
    generate_completion_report
    send_notification "🤖 自动化工程已交接" "已启动无人值守系统（driver/web-ui-driver 自动实现，完工自停）"

    log "INFO" "自动化工程工作流完成（实现已交接无人值守系统）"
}

# 执行
main "$@"
