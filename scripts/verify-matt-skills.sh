#!/bin/bash
# Matt 技能配置验证脚本

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=================================================="
echo "  Matt 技能配置验证"
echo "  项目: AI-FanYi"
echo "  路径: $PROJECT_ROOT"
echo "=================================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查函数
check_file() {
    local file=$1
    local desc=$2

    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $desc: $file"
        return 0
    else
        echo -e "${RED}✗${NC} $desc: $file (缺失)"
        return 1
    fi
}

check_section() {
    local file=$1
    local section=$2
    local desc=$3

    if grep -q "$section" "$file" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $desc"
        return 0
    else
        echo -e "${RED}✗${NC} $desc (缺失)"
        return 1
    fi
}

# 1. 检查 CLAUDE.md
echo "1. 检查 CLAUDE.md"
echo "   ──────────────────────────────────"
if check_file "CLAUDE.md" "CLAUDE.md"; then
    check_section "CLAUDE.md" "## Agent Skills" "   Agent Skills 部分"
    check_section "CLAUDE.md" "Issue Tracker" "   Issue Tracker 引用"
    check_section "CLAUDE.md" "Triage Labels" "   Triage Labels 引用"
    check_section "CLAUDE.md" "Domain Docs" "   Domain Docs 引用"
fi
echo ""

# 2. 检查 docs/agents/
echo "2. 检查 docs/agents/ 配置"
echo "   ──────────────────────────────────"
check_file "docs/agents/issue-tracker.md" "Issue Tracker 配置"
check_file "docs/agents/triage-labels.md" "Triage Labels 配置"
check_file "docs/agents/domain.md" "Domain Docs 配置"
echo ""

# 3. 检查 CONTEXT.md
echo "3. 检查领域文档"
echo "   ──────────────────────────────────"
check_file "CONTEXT.md" "CONTEXT.md"
check_file "docs/adr/" "docs/adr/ 目录" || echo "   (ADR 目录不存在，将自动创建)"
echo ""

# 4. 检查技能链接
echo "4. 检查 Matt 技能安装"
echo "   ──────────────────────────────────"
SKILLS_DIR="$HOME/.pi/agent/skills"
REQUIRED_SKILLS=(
    "grill-me"
    "grill-with-docs"
    "to-spec"
    "to-tickets"
    "implement"
    "code-review"
    "triage"
    "domain-modeling"
)

for skill in "${REQUIRED_SKILLS[@]}"; do
    if [ -L "$SKILLS_DIR/$skill" ] || [ -d "$SKILLS_DIR/$skill" ]; then
        echo -e "${GREEN}✓${NC} $skill"
    else
        echo -e "${RED}✗${NC} $skill (未安装)"
    fi
done
echo ""

# 5. 检查 git 仓库
echo "5. 检查 Git 仓库"
echo "   ──────────────────────────────────"
if [ -d ".git" ]; then
    echo -e "${GREEN}✓${NC} Git 仓库已初始化"

    # 检查远程仓库
    if git remote -v | grep -q "github.com"; then
        echo -e "${GREEN}✓${NC} GitHub 远程仓库已配置"
        git remote -v | head -2 | sed 's/^/   /'
    else
        echo -e "${YELLOW}⚠${NC} 未检测到 GitHub 远程仓库"
    fi
else
    echo -e "${RED}✗${NC} 不是 Git 仓库"
fi
echo ""

# 6. 检查依赖
echo "6. 检查项目依赖"
echo "   ──────────────────────────────────"
if [ -f "requirements.txt" ]; then
    echo -e "${GREEN}✓${NC} requirements.txt 存在"
else
    echo -e "${YELLOW}⚠${NC} requirements.txt 不存在"
fi

if [ -f "pyproject.toml" ]; then
    echo -e "${GREEN}✓${NC} pyproject.toml 存在"
else
    echo -e "${YELLOW}⚠${NC} pyproject.toml 不存在"
fi
echo ""

# 7. 检查文档
echo "7. 检查项目文档"
echo "   ──────────────────────────────────"
DOCS=(
    "README.md"
    "CONTEXT.md"
    "CLAUDE.md"
    "docs/MATT_SKILLS_GUIDE.md"
)

for doc in "${DOCS[@]}"; do
    check_file "$doc" "$doc"
done
echo ""

# 总结
echo "=================================================="
echo "  配置验证完成"
echo "=================================================="
echo ""
echo "下一步操作："
echo "  1. 开始使用: /grill-me"
echo "  2. 查看指南: cat docs/MATT_SKILLS_GUIDE.md"
echo "  3. 更新配置: /setup-matt-pocock-skills"
echo ""
