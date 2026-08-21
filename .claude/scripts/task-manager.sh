#!/bin/bash
# 任务管理器 - 集成进度保存和额度检查

PROGRESS_DIR=".claude"
PROGRESS_FILE="$PROGRESS_DIR/task-progress.yaml"
CONTEXT_FILE="$PROGRESS_DIR/context-summary.md"
QUOTA_FILE="$PROGRESS_DIR/quota-usage.json"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 帮助信息
show_help() {
    cat << EOF
任务管理器 - 管理长期任务的进度和额度

用法:
    task-manager.sh <command> [options]

命令:
    start <task-id>        开始一个新任务
    progress <phase> <msg> 保存当前进度
    context [summary]     保存上下文摘要
    resume                从进度恢复任务
    status               查看当前状态
    quota               检查 API 额度
    save                保存完整进度（上下文+状态）

示例:
    # 开始新任务
    ./task-manager.sh start implement-m01

    # 保存进度
    ./task-manager.sh progress api-endpoints "完成 CRUD 端点"

    # 保存上下文
    ./task-manager.sh context "数据库模型已完成，下一步实现 API"

    # 恢复任务
    ./task-manager.sh resume

    # 查看状态
    ./task-manager.sh status
EOF
}

# 开始新任务
start_task() {
    local task_id=$1
    local task_dir="$PROGRESS_DIR/tasks/$task_id"

    echo -e "${GREEN}开始新任务: $task_id${NC}"
    mkdir -p "$task_dir"

    # 初始化进度文件
    cat > "$PROGRESS_FILE" << EOF
task_id: "$task_id"
started_at: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
last_update: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
status: "in_progress"

current_phase:
  id: "init"
  status: "pending"
  message: "任务初始化"
  updated_at: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

resume_prompt: |
  恢复任务: $task_id
  任务状态: 初始化完成，准备开始执行
EOF

    # 创建空白上下文文件
    cat > "$CONTEXT_FILE" << EOF
# 任务: $task_id

**开始时间**: $(date '+%Y-%m-%d %H:%M:%S')

## 任务目标


## 已完成


## 进行中


## 待完成


## 下一步


EOF

    echo -e "${GREEN}✓ 任务已初始化${NC}"
    echo "  任务ID: $task_id"
    echo "  进度文件: $PROGRESS_FILE"
    echo "  上下文文件: $CONTEXT_FILE"
}

# 保存进度
save_progress() {
    local phase=$1
    local message=$2

    if [ -z "$phase" ]; then
        echo -e "${RED}错误: 请指定阶段名称${NC}"
        exit 1
    fi

    bash "$PROGRESS_DIR/scripts/save-progress.sh" \
        "$(yaml_get_value 'task_id')" \
        "in_progress" \
        "$phase" \
        "$message"

    echo ""
    echo -e "${GREEN}✓ 进度已保存${NC}"
}

# 保存上下文
save_context() {
    local summary=$1

    if [ -n "$summary" ]; then
        echo "$summary" > "$CONTEXT_FILE.tmp"
        mv "$CONTEXT_FILE.tmp" "$CONTEXT_FILE"
    fi

    echo -e "${GREEN}✓ 上下文已保存: $CONTEXT_FILE${NC}"
}

# 检查额度
check_quota() {
    if command -v python3 &> /dev/null; then
        python3 "$PROGRESS_DIR/scripts/check-quota.py"
    else
        echo -e "${YELLOW}⚠️  Python3 未安装，无法检查额度${NC}"
    fi
}

# 保存完整状态
save_all() {
    echo -e "${GREEN}保存完整状态...${NC}"
    echo ""

    # 检查额度
    echo "1. 检查 API 额度..."
    check_quota
    echo ""

    # 保存进度
    echo "2. 保存任务进度..."
    if [ -f "$PROGRESS_FILE" ]; then
        cp "$PROGRESS_FILE" "$PROGRESS_FILE.backup"
        echo "  ✓ 已备份进度文件"
    fi
    echo ""

    # 提示用户更新上下文
    echo "3. 上下文摘要..."
    if [ -f "$CONTEXT_FILE" ]; then
        echo "  当前摘要内容:"
        head -10 "$CONTEXT_FILE"
        echo ""
        echo "  编辑摘要: nano $CONTEXT_FILE"
    else
        echo "  ⚠️  未找到上下文文件"
    fi
    echo ""

    echo -e "${GREEN}✓ 状态保存完成${NC}"
    echo ""
    echo "恢复时使用:"
    echo "  ./task-manager.sh resume"
}

# 恢复任务
resume_task() {
    echo -e "${GREEN}从进度恢复任务${NC}"
    echo ""

    bash "$PROGRESS_DIR/scripts/resume.sh"
}

# 查看状态
show_status() {
    echo -e "${GREEN}当前任务状态${NC}"
    echo ""

    # 进度文件
    if [ -f "$PROGRESS_FILE" ]; then
        echo "📋 进度文件:"
        cat "$PROGRESS_FILE"
        echo ""
    else
        echo -e "${YELLOW}⚠️  未找到进度文件${NC}"
        echo ""
    fi

    # 额度状态
    if command -v python3 &> /dev/null; then
        echo "💰 额度状态:"
        python3 "$PROGRESS_DIR/scripts/check-quota.py" 2>/dev/null || echo "  无法检查额度"
        echo ""
    fi

    # 上下文摘要（前几行）
    if [ -f "$CONTEXT_FILE" ]; then
        echo "📖 上下文摘要 (预览):"
        head -15 "$CONTEXT_FILE"
        echo ""
        echo "  查看完整: cat $CONTEXT_FILE"
        echo ""
    fi
}

# YAML 辅助函数（简化版）
yaml_get_value() {
    local key=$1
    grep "^${key}:" "$PROGRESS_FILE" 2>/dev/null | sed "s/${key}: //" | sed 's/"//g'
}

# 主函数
main() {
    # 确保目录存在
    mkdir -p "$PROGRESS_DIR/scripts"

    # 确保脚本存在
    for script in save-progress.sh save-context.sh resume.sh check-quota.py; do
        if [ ! -f "$PROGRESS_DIR/scripts/$script" ]; then
            echo -e "${YELLOW}⚠️  缺少脚本: $script${NC}"
        fi
    done

    # 解析命令
    case "${1:-}" in
        start)
            start_task "${2:-task-$(date +%Y%m%d-%H%M%S)}"
            ;;
        progress)
            save_progress "$2" "$3"
            ;;
        context)
            save_context "$2"
            ;;
        resume)
            resume_task
            ;;
        status)
            show_status
            ;;
        quota)
            check_quota
            ;;
        save)
            save_all
            ;;
        help|--help|-h|"")
            show_help
            ;;
        *)
            echo -e "${RED}未知命令: $1${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
