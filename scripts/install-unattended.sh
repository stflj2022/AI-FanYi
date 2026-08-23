#!/bin/bash
# AI-FanYi 无人值守开发系统 - 安装脚本

set -e

# 服务名称列表（与卸载脚本保持一致）
SERVICES="aifanyi-driver.service aifanyi-watchdog.service aifanyi-watchdog.timer aifanyi-progress-report.service aifanyi-progress-report.timer"

# POSIX 兼容的路径获取方式
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SYSTEMD_DIR="$PROJECT_DIR/systemd"
USER_SYSTEMD_DIR="$HOME/.config/systemd/user"

echo "========================================"
echo "AI-FanYi 无人值守开发系统 - 安装"
echo "========================================"
echo ""

# 检查必要工具
for cmd in systemctl tmux notify-send; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "❌ 错误: 未找到 $cmd"
        echo "   请安装后再运行此脚本"
        exit 1
    fi
done

echo "✅ 必要工具检查通过"
echo ""

# 若存在旧的「完工停止」标记，重装即视为重新启用，清除之；
# 若项目实际尚未完工而标记仍在，看门狗/汇报会永久静默。
if [ -f "$PROJECT_DIR/.claude/UNATTENDED_STOPPED" ]; then
    echo "⚠️  检测到旧的完工停止标记，已清除（重装视为重新启用）"
    rm -f "$PROJECT_DIR/.claude/UNATTENDED_STOPPED"
fi
rm -f "$PROJECT_DIR/.claude/.shutdown.lock"

# 创建用户 systemd 目录
mkdir -p "$USER_SYSTEMD_DIR"

# 复制服务文件
echo "📦 安装 systemd 服务文件..."
cp "$SYSTEMD_DIR/aifanyi-driver.service" "$USER_SYSTEMD_DIR/"
cp "$SYSTEMD_DIR/aifanyi-watchdog.service" "$USER_SYSTEMD_DIR/"
cp "$SYSTEMD_DIR/aifanyi-watchdog.timer" "$USER_SYSTEMD_DIR/"
cp "$SYSTEMD_DIR/aifanyi-progress-report.service" "$USER_SYSTEMD_DIR/"
cp "$SYSTEMD_DIR/aifanyi-progress-report.timer" "$USER_SYSTEMD_DIR/"

echo "✅ 服务文件已复制到 $USER_SYSTEMD_DIR"
echo ""

# 重新加载 systemd
echo "🔄 重新加载 systemd 配置..."
systemctl --user daemon-reload
echo "✅ systemd 配置已重新加载"
echo ""

# 启用并启动服务
echo "🚀 启用并启动服务..."

# 启用并启动 driver
systemctl --user enable aifanyi-driver.service
systemctl --user start aifanyi-driver.service
echo "✅ aifanyi-driver.service 已启动"

# 启用并启动 watchdog
systemctl --user enable aifanyi-watchdog.timer
systemctl --user start aifanyi-watchdog.timer
echo "✅ aifanyi-watchdog.timer 已启动（每10分钟检查）"

# 启用并启动 progress-report
systemctl --user enable aifanyi-progress-report.timer
systemctl --user start aifanyi-progress-report.timer
echo "✅ aifanyi-progress-report.timer 已启动（每30分钟汇报）"
echo ""
echo "ℹ️  完工自停：当 docs/tickets 全部 done 时，驱动/看门狗/汇报会自动停止并禁用，"
echo "   只发送一次终报通知（见 scripts/shutdown-unattended.sh）"

# 等待服务启动
sleep 2

# 检查服务状态
echo "📊 服务状态："
echo ""
systemctl --user status aifanyi-driver.service --no-pager | head -10
echo ""
systemctl --user list-timers aifanyi* | grep -E "aifanyi|NEXT|LEFT"
echo ""

# 测试通知
echo "🔔 测试桌面通知..."
notify-send \
    --app-name="AI-FanYi" \
    --icon="dialog-information" \
    --urgency="normal" \
    --expire-time=5000 \
    "✅ AI-FanYi 安装完成" \
    "无人值守开发系统已成功启动！"
echo "✅ 通知测试完成"
echo ""

echo "========================================"
echo "🎉 安装完成！"
echo "========================================"
echo ""
echo "📋 常用命令："
echo "  查看驱动日志:     tail -f $PROJECT_DIR/.claude/pi-driver.log"
echo "  查看汇报日志:     tail -f $PROJECT_DIR/.claude/progress-report.log"
echo "  查看服务状态:     systemctl --user status aifanyi-driver.service"
echo "  查看定时器:       systemctl --user list-timers aifanyi*"
echo "  手动触发汇报:     $PROJECT_DIR/scripts/progress-report.sh"
echo "  查看最近汇报:     $PROJECT_DIR/scripts/view-reports.sh"
echo ""
echo "📚 详细文档: $PROJECT_DIR/docs/UNATTENDED_SYSTEM_COMPLETE.md"
echo ""
