#!/bin/bash
# AI-FanYi 推送到 GitHub

set -e

echo "======================================"
echo "AI-FanYi 推送到 GitHub"
echo "======================================"
echo ""

# 检查当前分支
CURRENT_BRANCH=$(git branch --show-current)
echo "当前分支: $CURRENT_BRANCH"

# 检查远程仓库
echo ""
echo "检查远程仓库..."
if ! git remote | grep -q "ai-fanyi"; then
    echo "添加 AI-FanYi 远程仓库..."
    git remote add ai-fanyi https://github.com/stflj2022/AI-FanYi.git
else
    echo "AI-FanYi 远程仓库已存在"
fi

echo ""
echo "远程仓库:"
git remote -v

echo ""
echo "======================================"
echo "准备推送到 https://github.com/stflj2022/AI-FanYi.git"
echo "======================================"
echo ""
read -p "按 Enter 继续推送，或 Ctrl+C 取消..."

# 推送到 master 分支
echo ""
echo "推送中..."
git push ai-fanyi $CURRENT_BRANCH:master --force

echo ""
echo "======================================"
echo "✓ 推送完成！"
echo "======================================"
echo ""
echo "访问 https://github.com/stflj2022/AI-FanYi 查看仓库"
