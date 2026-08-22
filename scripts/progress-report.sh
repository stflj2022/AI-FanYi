#!/bin/bash
# AI-FanYi 监督系统进度汇报脚本

PROJECT_DIR="$HOME/桌面/AI-FanYi"
LOG_FILE="$PROJECT_DIR/.claude/pi-driver.log"
REPORT_FILE="$PROJECT_DIR/.claude/progress-report.log"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 用于通知的变量
REPORT_TIME=$(date '+%H:%M')
SERVICE_STATUS="未知"
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
if systemctl --user is-active --quiet aifanyi-driver.service; then
    echo -e "  ${GREEN}✅ aifanyi-driver.service 运行中${NC}" | tee -a "$REPORT_FILE"
    SERVICE_STATUS="✅ 运行中"
    systemctl --user show aifanyi-driver.service --property=ActiveState,MainPID,MemoryCurrent,CPUUsage | sed 's/^/  /' | tee -a "$REPORT_FILE"
else
    echo -e "  ${RED}❌ aifanyi-driver.service 未运行${NC}" | tee -a "$REPORT_FILE"
    SERVICE_STATUS="❌ 未运行"
fi
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
    # 统计工单状态
    TICKETS_TOTAL=$(find docs/tickets -name "*.md" -type f | wc -l)
    echo "  总工单数: $TICKETS_TOTAL" | tee -a "$REPORT_FILE"

    # 检查是否有 blocked 工单
    TICKETS_BLOCKED=$(grep -l "status: blocked" docs/tickets/*.md 2>/dev/null | wc -l)
    if [ "$TICKETS_BLOCKED" -gt 0 ]; then
        echo -e "  ${YELLOW}⚠️  $TICKETS_BLOCKED 个工单被阻塞${NC}" | tee -a "$REPORT_FILE"
    fi

    # 检查已完成工单
    TICKETS_DONE=$(grep -l "status: done" docs/tickets/*.md 2>/dev/null | wc -l)
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
    NOTIFICATION_BODY="📊 $SERVICE_STATUS\n"
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
