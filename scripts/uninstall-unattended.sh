#!/bin/bash
# AI-FanYi 无人值守开发系统 - 卸载脚本

set -e

# 服务名称列表（与安装脚本保持一致）
SERVICES="aifanyi-driver.service aifanyi-watchdog.service aifanyi-watchdog.timer aifanyi-progress-report.service aifanyi-progress-report.timer"

echo "========================================"
echo "AI-FanYi 无人值守开发系统 - 卸载"
echo "========================================"
echo ""

# 确认（POSIX 兼容）
printf "确定要停止并卸载 AI-FanYi 无人值守系统吗？(y/N) "
read -r REPLY
echo ""
case "$REPLY" in
    [Yy]*) ;;
    *) echo "❌ 已取消卸载"; exit 0 ;;
esac

# 停止服务
echo "🛑 停止服务..."
systemctl --user stop aifanyi-progress-report.timer 2>/dev/null || true
systemctl --user stop aifanyi-watchdog.timer 2>/dev/null || true
systemctl --user stop aifanyi-driver.service 2>/dev/null || true
echo "✅ 服务已停止"

# 禁用服务
echo "🔄 禁用服务..."
systemctl --user disable aifanyi-progress-report.timer 2>/dev/null || true
systemctl --user disable aifanyi-watchdog.timer 2>/dev/null || true
systemctl --user disable aifanyi-driver.service 2>/dev/null || true
echo "✅ 服务已禁用"

# 删除服务文件
echo "🗑️  删除服务文件..."
rm -f "$HOME/.config/systemd/user/aifanyi-driver.service"
rm -f "$HOME/.config/systemd/user/aifanyi-watchdog.service"
rm -f "$HOME/.config/systemd/user/aifanyi-watchdog.timer"
rm -f "$HOME/.config/systemd/user/aifanyi-progress-report.service"
rm -f "$HOME/.config/systemd/user/aifanyi-progress-report.timer"
echo "✅ 服务文件已删除"

# 重新加载 systemd
echo "🔄 重新加载 systemd 配置..."
systemctl --user daemon-reload
echo "✅ systemd 配置已重新加载"

# 清理锁文件
echo "🧹 清理锁文件..."
rm -f /tmp/aifanyi-driver.lock
echo "✅ 锁文件已清理"

echo ""
echo "========================================"
echo "🎉 卸载完成！"
echo "========================================"
echo ""
echo "注意：以下文件未被删除，您可以根据需要手动清理："
echo "  - 日志文件: .claude/pi-driver.log"
echo "  - 汇报日志: .claude/progress-report.log"
echo "  - 项目状态文件: .claude/"
echo ""
