#!/bin/bash
# AI-FanYi 监督系统进度汇报脚本

# 动态检测项目目录（支持相对/绝对路径）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$PROJECT_DIR/.claude/pi-driver.log"
REPORT_FILE="$PROJECT_DIR/.claude/progress-report.log"

# 完工自停守卫：
# 1) 系统已停止过 → 静默退出，不再发任何通知（防止完工后每30分钟继续轰炸）
if [ -f "$PROJECT_DIR/.claude/UNATTENDED_STOPPED" ]; then
    exit 0
fi
# 2) 项目已完工 → 触发一站式停止（含唯一一次终报通知），不再发常规汇报
if "$SCRIPT_DIR/completion-check.sh" >/dev/null 2>&1; then
    "$SCRIPT_DIR/shutdown-unattended.sh" "项目完工（进度汇报触发）" || true
    exit 0
fi

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 用于通知的变量
REPORT_TIME=$(date '+%H:%M')
SERVICE_STATUS="未知"
WATCHDOG_STATUS="未知"
UNATTENDED_STATUS="未知"
LATEST_COMMIT="无"
TICKETS_TOTAL=0
TICKETS_DONE=0
TICKETS_BLOCKED=0
CPU_USAGE="0%"
MEMORY_USAGE="未知"

echo "========================================" | tee -a "$REPORT_FILE"
echo "AI-FanYi 监督系统进度汇报" | tee -a "$REPORT_FILE"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$REPORT_FILE"
echo "========================================" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# 1. 服务状态
echo -e "${BLUE}📊 服务状态${NC}" | tee -a "$REPORT_FILE"

# 检查 driver 服务
if systemctl --user is-active --quiet aifanyi-driver.service; then
    echo -e "  ${GREEN}✅ aifanyi-driver.service 运行中${NC}" | tee -a "$REPORT_FILE"
    SERVICE_STATUS="✅ 运行中"
    systemctl --user show aifanyi-driver.service --property=ActiveState,MainPID,MemoryCurrent,CPUUsage | sed 's/^/  /' | tee -a "$REPORT_FILE"
else
    echo -e "  ${RED}❌ aifanyi-driver.service 未运行${NC}" | tee -a "$REPORT_FILE"
    SERVICE_STATUS="❌ 未运行"
fi

# 检查 watchdog 服务（oneshot 类型，检查是否失败即可）
if systemctl --user is-failed --quiet aifanyi-watchdog.service; then
    echo -e "  ${RED}❌ aifanyi-watchdog.service 失败${NC}" | tee -a "$REPORT_FILE"
    WATCHDOG_STATUS="❌ 失败"
else
    # 检查 watchdog timer 是否运行
    if systemctl --user is-active --quiet aifanyi-watchdog.timer; then
        echo -e "  ${GREEN}✅ aifanyi-watchdog.service 正常（由 timer 定期触发）${NC}" | tee -a "$REPORT_FILE"
        WATCHDOG_STATUS="✅ 正常"
    else
        echo -e "  ${YELLOW}⚠️  aifanyi-watchdog.timer 未运行${NC}" | tee -a "$REPORT_FILE"
        WATCHDOG_STATUS="⚠️ Timer 未运行"
    fi
fi

# 综合判断 unattended-dev-system 状态
if systemctl --user is-active --quiet aifanyi-driver.service; then
    if systemctl --user is-active --quiet aifanyi-watchdog.timer && ! systemctl --user is-failed --quiet aifanyi-watchdog.service; then
        UNATTENDED_STATUS="✅ 正常"
    else
        UNATTENDED_STATUS="⚠️ 部分（watchdog 异常）"
    fi
else
    UNATTENDED_STATUS="❌ 异常"
fi

echo -e "  综合状态: $UNATTENDED_STATUS" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# 2. 最新日志摘要
echo -e "${BLUE}📝 最新日志 (最后 20 行)${NC}" | tee -a "$REPORT_FILE"
tail -20 "$LOG_FILE" 2>/dev/null | sed 's/^/  /' | tee -a "$REPORT_FILE" || echo "  (日志文件不存在)" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# 3. Git 状态
echo -e "${BLUE}🔀 Git 状态${NC}" | tee -a "$REPORT_FILE"
if [ -d "$PROJECT_DIR/.git" ]; then
    echo "  最新提交:" | tee -a "$REPORT_FILE"
    LATEST_COMMIT=$(cd "$PROJECT_DIR" && git log --oneline -1 2>/dev/null | cut -d' ' -f1,2,3,4)
    cd "$PROJECT_DIR" && git log --oneline -3 | sed 's/^/    /' | tee -a "$REPORT_FILE"
    echo "" | tee -a "$REPORT_FILE"
    echo "  当前分支: $(cd "$PROJECT_DIR" && git branch --show-current)" | tee -a "$REPORT_FILE"
    echo "  未提交文件:" | tee -a "$REPORT_FILE"
    cd "$PROJECT_DIR" && git status --short 2>/dev/null | sed 's/^/    /' || echo "    无" | tee -a "$REPORT_FILE"
else
    echo "  (不是 Git 仓库)" | tee -a "$REPORT_FILE"
fi
echo "" | tee -a "$REPORT_FILE"

# 4. 工单状态（如果存在）
if [ -d "$PROJECT_DIR/docs/tickets" ]; then
    echo -e "${BLUE}🎫 工单状态${NC}" | tee -a "$REPORT_FILE"
    cd "$PROJECT_DIR"
    # 统计工单状态（只统计 ticket-*.md，不包括 README.md）
    TICKETS_TOTAL=$(find docs/tickets -name "ticket-*.md" -type f | wc -l)
    echo "  总工单数: $TICKETS_TOTAL" | tee -a "$REPORT_FILE"

    # 检查是否有 blocked 工单
    TICKETS_BLOCKED=$(grep -l "^## 状态:.*blocked" docs/tickets/*.md 2>/dev/null | wc -l)
    if [ "$TICKETS_BLOCKED" -gt 0 ]; then
        echo -e "  ${YELLOW}⚠️  $TICKETS_BLOCKED 个工单被阻塞${NC}" | tee -a "$REPORT_FILE"
    fi

    # 检查已完成工单
    TICKETS_DONE=$(grep -l "^## 状态:.*done" docs/tickets/*.md 2>/dev/null | wc -l)
    echo "  已完成: $TICKETS_DONE" | tee -a "$REPORT_FILE"
    echo "" | tee -a "$REPORT_FILE"
fi

# 5. 系统资源
echo -e "${BLUE}💻 系统资源${NC}" | tee -a "$REPORT_FILE"
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%
MEMORY_USAGE=$(free -h | awk '/^Mem:/ {print $3 "/" $2}')
DISK_USAGE=$(df -h "$PROJECT_DIR" | awk 'NR==2 {print $3 "/" $2 " (" $5 ")"}')
echo "  CPU: $CPU_USAGE 使用" | tee -a "$REPORT_FILE"
echo "  内存: $MEMORY_USAGE" | tee -a "$REPORT_FILE"
echo "  磁盘: $DISK_USAGE" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

echo -e "${GREEN}========================================${NC}" | tee -a "$REPORT_FILE"
echo -e "${GREEN}汇报完成${NC}" | tee -a "$REPORT_FILE"
echo "========================================" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

# 发送桌面通知
if command -v notify-send >/dev/null 2>&1; then
    # 构建通知内容
    NOTIFICATION_BODY="📊 Driver: $SERVICE_STATUS | Watchdog: $WATCHDOG_STATUS\n"
    NOTIFICATION_BODY+="🤖 Unattended: $UNATTENDED_STATUS\n"
    NOTIFICATION_BODY+="🔀 最新: $LATEST_COMMIT\n"
    NOTIFICATION_BODY+="🎫 工单: $TICKETS_DONE/$TICKETS_TOTAL 完成"
    if [ "$TICKETS_BLOCKED" -gt 0 ]; then
        NOTIFICATION_BODY+=" ($TICKETS_BLOCKED 阻塞)"
    fi
    NOTIFICATION_BODY+="\n"
    NOTIFICATION_BODY+="💻 CPU: $CPU_USAGE | 内存: $MEMORY_USAGE"

    # 根据服务状态设置紧急程度和图标
    if systemctl --user is-active --quiet aifanyi-driver.service; then
        URGENCY="normal"
        ICON="dialog-information"
    else
        URGENCY="critical"
        ICON="dialog-error"
    fi

    # 发送通知（使用固定 replace-id 确保多次通知只保留最近一次）
    # expire-time=0 表示不自动消失，需要手动点击关闭
    notify-send \
        --app-name="AI-FanYi" \
        --icon="$ICON" \
        --urgency="$URGENCY" \
        --replace-id=1001 \
        --expire-time=0 \
        "📋 AI-FanYi 进度汇报 [$REPORT_TIME]" \
        "$NOTIFICATION_BODY"
fi
