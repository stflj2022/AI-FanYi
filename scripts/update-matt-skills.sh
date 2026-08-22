#!/bin/bash
# update.sh — Update Matt Pocock skills to the latest version
# Official source: https://github.com/mattpocock/skills
# This repo uses a git submodule pointing at the official upstream.

set -e

echo "═══════════════════════════════════════════════════════════════"
echo "  Matt Pocock Skills - Auto Updater"
echo "  Source: https://github.com/mattpocock/skills"
echo "═══════════════════════════════════════════════════════════════"

# Where this repo is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
SUBMODULE_DIR="$REPO_ROOT/matt-pocock-skills"

cd "$REPO_ROOT"

echo ""
echo "📦 Step 1: Initializing submodule (if not yet cloned)..."
git submodule update --init --recursive

echo ""
echo "🔄 Step 2: Fetching latest from official upstream (mattpocock/skills)..."
cd "$SUBMODULE_DIR"
git fetch origin

echo "🎯 Step 3: Checking out latest version..."
# Resolve the upstream default branch robustly (works regardless of locale)
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@refs/remotes/origin/@@')
[ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH="main"
echo "  → Upstream default branch: $DEFAULT_BRANCH"
git checkout "$DEFAULT_BRANCH"
git pull origin "$DEFAULT_BRANCH"

cd "$REPO_ROOT"
echo ""
echo "✅ Committing submodule pointer update..."
git add matt-pocock-skills
git commit -m "chore: update matt-pocock-skills submodule to $(cd "$SUBMODULE_DIR" && git rev-parse --short HEAD)" --allow-empty 2>/dev/null || true

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  ✅ Matt Pocock skills updated successfully!"
echo "  Latest commit: $(cd "$SUBMODULE_DIR" && git log --oneline -1)"
echo ""
echo "  Skills now available (see matt-pocock-skills/skills/):"
echo "    - engineering/  (18 skills, plugin-ready)"
echo "    - productivity/ (7 skills, general workflow)"
echo "    - in-progress/  (6 skills, beta)"
echo "    - misc/         (4 skills)"
echo "═══════════════════════════════════════════════════════════════"
