#!/bin/bash
# 简化推送脚本

echo "======================================"
echo "推送到 GitHub"
echo "======================================"
echo ""
echo "远程仓库: https://github.com/stflj2022/AI-FanYi.git"
echo ""
echo "当前提交:"
git log --oneline -2
echo ""
echo "准备推送..."
echo ""

# 推送命令
git push ai-fanyi $(git branch --show-current):master --force

echo ""
echo "======================================"
if [ $? -eq 0 ]; then
    echo "✓ 推送成功！"
else
    echo "✗ 推送失败"
    echo ""
    echo "可能的原因:"
    echo "  1. 网络连接问题"
    echo "  2. GitHub 认证问题"
    echo "  3. 需要配置 GitHub Token"
    echo ""
    echo "尝试手动推送:"
    echo "  git push ai-fanyi master:master --force"
    echo ""
    echo "或使用 Token:"
    echo "  git push https://YOUR_TOKEN@github.com/stflj2022/AI-FanYi.git master"
fi
echo "======================================"
