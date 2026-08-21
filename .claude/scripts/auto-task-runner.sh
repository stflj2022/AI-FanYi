#!/bin/bash
# 自动任务执行器 - 无需人工值守
# 自动处理进度保存、额度监控、等待重置、恢复执行

set -e

# ============================================
# 配置
# ============================================

PROGRESS_DIR=".claude"
TASK_FILE="$PROGRESS_DIR/current-task.yaml"
CONTEXT_FILE="$PROGRESS_DIR/context-summary.md"
QUOTA_FILE="$PROGRESS_DIR/quota-usage.json"
CHECK_INTERVAL=300  # 每5分钟检查一次
QUOTA_THRESHOLD=80   # 额度使用超过80%时保存

# ============================================
# 工具函数
# ============================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ $*" >&2
}

log_success() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ $*"
}

log_warning() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  $*" >&2
}

# ============================================
# 额度检查
# ============================================

check_quota() {
    if [ ! -f "$QUOTA_FILE" ]; then
        # 创建初始额度文件
        cat > "$QUOTA_FILE" << EOF
{
  "last_reset": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "tokens_used": 0,
  "last_check": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "max_quota": 1000000
}
EOF
        echo "0"
        return
    fi

    # 读取使用量
    python3 -c "
import json
from datetime import datetime

with open('$QUOTA_FILE') as f:
    data = json.load(f)

last_reset = datetime.fromisoformat(data['last_check'])
now = datetime.now()
elapsed = (now - last_reset).total_seconds()

# 如果超过5小时，视为重置
if elapsed > 5 * 3600:
    print('0')
else:
    print(str(data.get('tokens_used', 0)))
" 2>/dev/null || echo "0"
}

update_quota() {
    local tokens=$1
    python3 -c "
import json
from datetime import datetime

with open('$QUOTA_FILE', 'r') as f:
    data = json.load(f)

data['tokens_used'] = max(0, data.get('tokens_used', 0) + $tokens)
data['last_check'] = datetime.now().isoformat()

with open('$QUOTA_FILE', 'w') as f:
    json.dump(data, f, indent=2)
"
}

get_time_until_reset() {
    python3 -c "
import json
from datetime import datetime

try:
    with open('$QUOTA_FILE') as f:
        data = json.load(f)
    last_reset = datetime.fromisoformat(data['last_check'])
    now = datetime.now()
    elapsed = (now - last_reset).total_seconds()
    remaining = 5 * 3600 - elapsed
    if remaining < 0:
        remaining = 0
    print(str(int(remaining)))
except:
    print(str(5 * 3600))
" 2>/dev/null || echo "18000"
}

# ============================================
# 进度管理
# ============================================

save_checkpoint() {
    local phase=$1
    local message=$2
    local auto_resume_prompt=$3

    mkdir -p "$PROGRESS_DIR"

    cat > "$TASK_FILE" << EOF
# 自动任务进度
# 由 auto-task-runner.sh 生成

task_id: "$(yaml_get 'task_id' 'auto-task')"
last_update: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
status: "in_progress"

current_phase:
  id: "$phase"
  status: "completed"
  message: "$message"
  completed_at: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

next_phase:
  id: "$(yaml_get 'next_phase' 'continue')"
  auto_resume: "$auto_resume_prompt"

checkpoint_count: $(($(yaml_get 'checkpoint_count' '0') + 1))
last_checkpoint: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

auto_resume_instruction: |
  ⚡ 自动恢复指令 ⚡
  任务在 $(date '+%Y-%m-%d %H:%M:%S') 自动保存进度
  原因: 额度管理或检查点保存

  请阅读 $CONTEXT_FILE 了解详细上下文
  然后继续执行: $auto_resume_prompt

system_info:
  quota_used: $(check_quota)
  time_until_reset: $(get_time_until_reset)
  hostname: $(hostname)
EOF

    log_success "检查点已保存: $phase"
}

yaml_get() {
    local key=$1
    local default=$2
    if [ -f "$TASK_FILE" ]; then
        grep "^${key}:" "$TASK_FILE" 2>/dev/null | sed "s/${key}: //" | sed 's/"//g' | head -1 || echo "$default"
    else
        echo "$default"
    fi
}

# ============================================
# 自动等待重置
# ============================================

wait_for_reset() {
    local seconds=$1

    if [ "$seconds" -le 0 ]; then
        return 0
    fi

    local hours=$((seconds / 3600))
    local minutes=$(((seconds % 3600) / 60))

    log "等待额度重置: ${hours}小时${minutes}分钟"
    log "重置预计时间: $(date -d "+${seconds} seconds" '+%Y-%m-%d %H:%M:%S')"

    # 创建等待标记文件
    cat > "$PROGRESS_DIR/waiting-for-reset.yaml" << EOF
waiting: true
start_time: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
expected_reset_time: "$(date -d "+${seconds} seconds" -u +%Y-%m-%dT%H:%M:%SZ)"
current_task: "$(yaml_get 'task_id' 'unknown')"
EOF

    # 等待（带定期检查）
    local elapsed=0
    while [ $elapsed -lt $seconds ]; do
        local remaining=$((seconds - elapsed))
        local sleep_time=$((remaining < 300 ? remaining : 300))  # 最多睡5分钟

        if [ $sleep_time -gt 0 ]; then
            sleep $sleep_time
        fi

        elapsed=$((elapsed + sleep_time))

        # 每5分钟报告一次
        if [ $((elapsed % 300)) -eq 0 ]; then
            local hours_left=$((remaining / 3600))
            local minutes_left=$(((remaining % 3600) / 60))
            log "等待中... 剩余 ${hours_left}小时${minutes_left}分钟"
        fi
    done

    # 额度已重置
    log_success "额度已重置！"
    rm -f "$PROGRESS_DIR/waiting-for-reset.yaml"

    # 重置额度计数
    cat > "$QUOTA_FILE" << EOF
{
  "last_reset": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "tokens_used": 0,
  "last_check": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "max_quota": 1000000
}
EOF
}

# ============================================
# 自动恢复提示生成
# ============================================

generate_resume_prompt() {
    local task_file="$1"
    local context_file="$2"

    cat << 'EOF'
╔══════════════════════════════════════════════════════════════════╗
║                    🤖 自动任务恢复指令 🤖                         ║
╚══════════════════════════════════════════════════════════════════╝

@Claude 继续执行自动任务

═════════════════════════════════════════════════════════════════════
📋 任务信息
═════════════════════════════════════════════════════════════════════

EOF

    if [ -f "$task_file" ]; then
        echo "任务文件: $task_file"
        cat "$task_file" | grep -E "^task_id:|^status:|^current_phase:" | sed 's/:/: /' | sed 's/^/  /'
        echo ""
    fi

    if [ -f "$context_file" ]; then
        echo "═════════════════════════════════════════════════════════════════════"
        echo "📖 上下文摘要"
        echo "═════════════════════════════════════════════════════════════════════"
        echo ""
        cat "$context_file"
        echo ""
    fi

    cat << 'EOF'
═════════════════════════════════════════════════════════════════════
🔧 执行指令
═════════════════════════════════════════════════════════════════════

请根据上述任务信息和上下文，继续执行下一步工作。
完成后，请运行: make task-auto-save PHASE=next-phase MESSAGE="完成说明"

═════════════════════════════════════════════════════════════════════
EOF
}

# ============================================
# 主函数
# ============================================

main() {
    local command="${1:-start}"
    shift || true

    case "$command" in
        start)
            log "开始自动任务执行"
            log "任务ID: ${1:-auto-task-$(date +%Y%m%d-%H%M%S)}"
            # 初始化任务
            ;;
        check)
            local used=$(check_quota)
            local max=1000000
            local percentage=$((used * 100 / max))

            log "额度检查: ${used}/${max} (${percentage}%)"

            if [ $percentage -ge $QUOTA_THRESHOLD ]; then
                log_warning "额度超过阈值，保存进度并等待重置"
                save_checkpoint "quota-checkpoint" "额度${percentage}%，自动保存" "等待额度重置后继续当前任务"
                wait_for_reset $(get_time_until_reset)
            fi
            ;;
        checkpoint)
            save_checkpoint "$1" "$2" "$3"
            ;;
        wait-reset)
            wait_for_reset $(get_time_until_reset)
            ;;
        resume-prompt)
            generate_resume_prompt "$TASK_FILE" "$CONTEXT_FILE"
            ;;
        monitor)
            # 持续监控模式
            log "启动持续监控模式"
            while true; do
                main check
                sleep $CHECK_INTERVAL
            done
            ;;
        *)
            echo "用法: $0 {start|check|checkpoint|wait-reset|resume-prompt|monitor}"
            exit 1
            ;;
    esac
}

main "$@"
