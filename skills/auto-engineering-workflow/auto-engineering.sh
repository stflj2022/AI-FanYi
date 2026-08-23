#!/bin/bash
# 自动化工程开发工作流 - 主驱动脚本

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

# Phase 4-7: 自动实现循环
phase4_implement_loop() {
    log "INFO" "=== Phase 4: 自动实现循环 ==="

    local tickets=$(get_sorted_tickets)

    for ticket in $tickets; do
        log "INFO" "处理 ticket: $ticket"

        # 检查依赖
        if ! dependencies_met "$ticket"; then
            log "INFO" "依赖未满足，跳过: $ticket"
            continue
        fi

        # 实现功能
        log "INFO" "实现 ticket: $ticket"
        /implement "$ticket"

        # 代码审查（必须通过）
        code_review_loop

        # 提交推送
        git_commit_and_push "$ticket"

        # 更新 ticket 状态
        update_ticket_status "$ticket" "done"

        # 更新完成计数
        yq -i ".completed_tickets += 1" "$STATUS_FILE"

        # 进度报告
        send_progress_report

        log "INFO" "Ticket 完成: $ticket"
    done
}

# 代码审查循环
code_review_loop() {
    local max_attempts=$(yq '.code_review.max_review_attempts' "$CONFIG_FILE")
    local review_count=0

    while true; do
        log "INFO" "代码审查第 $((review_count + 1)) 轮"

        # 调用 Matt Skill
        /code-review HEAD~1

        if has_review_findings; then
            if [ $review_count -ge $max_attempts ]; then
                log "ERROR" "代码审查多次失败，需要人工介入"
                send_notification "❌ 代码审查失败" "ticket ${CURRENT_TICKET} 代码审查 $max_attempts 次失败" "critical"
                break
            fi

            log "INFO" "发现审查问题，自动修复..."
            fix_review_issues
            review_count=$((review_count + 1))
        else
            log "INFO" "代码审查通过"
            break
        fi
    done
}

# Git 提交和推送
git_commit_and_push() {
    local ticket="$1"
    local ticket_title=$(get_ticket_title "$ticket")

    log "INFO" "提交 ticket: $ticket"

    # 提交
    git add -A
    git commit -m "feat($ticket): $ticket_title"

    # 推送到配置的目标仓库（origin/main 或其他配置的仓库）
    git push "$GIT_TARGET_REMOTE" "$GIT_TARGET_BRANCH"

    log "INFO" "已推送到: $GIT_TARGET_REMOTE/$GIT_TARGET_BRANCH"
}

# 进度报告
send_progress_report() {
    local total=$(yq '.total_tickets' "$STATUS_FILE")
    local completed=$(yq '.completed_tickets' "$STATUS_FILE")
    local phase=$(yq '.current_phase' "$STATUS_FILE")

    local message="当前阶段: $phase\n完成: $completed/$total\n仓库: $GIT_TARGET_REMOTE/$GIT_TARGET_BRANCH"

    send_notification "🚀 自动化工程进度" "$message"
}

# 生成完成报告
generate_completion_report() {
    log "INFO" "生成完成报告..."

    local report_file="$PROJECT_ROOT/.auto-engineering-report.md"
    local total=$(yq '.total_tickets' "$STATUS_FILE")
    local completed=$(yq '.completed_tickets' "$STATUS_FILE")
    local start_time=$(yq '.start_time' "$STATUS_FILE")
    local end_time=$(date +"%Y-%m-%dT%H:%M:%S%z")  # POSIX 兼容

    cat > "$report_file" << EOF
# 工程完成报告

## 项目信息
- 项目名称: $(yq '.project_name' "$STATUS_FILE")
- 完成时间: $end_time
- 总耗时: 计算中...

## 统计
- 总 Tickets: $total
- 已完成: $completed
- 完成率: $(awk "BEGIN {printf \"%.1f%%\", ($completed/$total)*100}")
- Git 提交数: $(git rev-list --count HEAD)
- 代码审查次数: 计算中...

## 生成的文件
- 规范文档: 查看 issue tracker
- Tickets: 查看 issue tracker
- 代码提交: $GITHUB_OWNER/$GITHUB_REPO

## 执行日志
详见: .auto-engineering-log.md

---

**自动化工程工作流完成**
EOF

    log "INFO" "完成报告已生成: $report_file"
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

    # Phase 4-7: 自动实现
    yq -i ".current_phase = \"phase4\"" "$STATUS_FILE"
    phase4_implement_loop

    # 完成
    generate_completion_report
    send_notification "🎉 自动化工程完成" "所有任务已完成，查看报告: .auto-engineering-report.md"

    log "INFO" "自动化工程工作流完成"
}

# 执行
main "$@"
