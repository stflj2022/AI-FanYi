# Matt Pocock Skills — 自动更新说明

## 原始仓库（Upstream）

- **GitHub**: https://github.com/mattpocock/skills
- **作者**: Matt Pocock (`mattpocock`)

> 本目录是官方仓库的 **git submodule 引用**，不是副本。它始终指向上游官方仓库，
> 因此可以随时拉取最新版本，与上游保持同步。

## 仓库结构

官方仓库 `skills/` 下分四类：

| 分类 | 数量 | 说明 |
|------|------|------|
| `engineering/` | 18 | 已进插件，日常编码 |
| `productivity/` | 7 | 已进插件，通用流程 |
| `in-progress/` | 6 | beta，可能改/删 |
| `misc/` | 4 | 作者自用，不进插件 |
| `deprecated/` | — | 已下架，不建议安装 |

## 如何安装 / 使用

### 方式一：Claude Code 插件（推荐，只读、自动更新）
```bash
claude plugins install mattpocock-skills
```
或在会话内：`/plugin install mattpocock-skills`

### 方式二：其他 agent（Codex 等），获取可编辑副本
```bash
npx skills@latest add mattpocock/skills
```
只装某个 beta 技能：
```bash
npx skills@latest add mattpocock/skills --skill=loop-me
```

### 方式三：手动 clone（本仓库已用 submodule 引用）
直接 clone 或 submodule update，扔进 `~/.claude/skills/`（全局）或项目的 `.claude/`（项目级）。
项目级配置优先于全局配置。

## 首次使用

每个项目第一次接入时，先跑一次初始化：
```
/setup-matt-pocock-skills
```
它会询问：① 用哪个 issue 跟踪器 ② triage 标签放哪 ③ 文档存哪。
后续所有工程类技能都依赖这个结果，务必先跑。
之后可用 `/ask-matt` 查看从哪个技能切入。

## 如何自动更新

本仓库内置一键更新脚本：

```bash
# 在 skill-j 仓库根目录
bash scripts/update-matt-skills.sh
```

脚本会：
1. 初始化 submodule（如尚未 clone）
2. 从官方上游 `mattpocock/skills` 拉取最新
3. checkout 到上游默认分支的最新提交
4. 提交 submodule 指针更新

### 手动更新方式

```bash
# 方式 A：本仓库 submodule 一键更新（推荐）
git submodule update --remote matt-pocock-skills

# 方式 B：进入 submodule 直接 pull
cd matt-pocock-skills
git fetch origin
git checkout main   # 或上游默认分支
git pull origin main
cd ..
git add matt-pocock-skills
git commit -m "chore: update matt-pocock-skills"
git push origin main
```

## 依赖关系

| 子技能 | 说明 |
|--------|------|
| `grill-me` | 通过 interview 磨炼方案 |
| `to-spec` | 把对话转成 spec |
| `to-tickets` | 把 spec 拆成任务 |
| `implement` | 从 spec/tickets 构建 |
| `grill-with-docs` | 带文档审查的设计访谈 |
| `setup-matt-pocock-skills` | 首次初始化（必跑） |
| `ask-matt` | 选择切入技能入口 |

---
**同步对象**: `mattpocock/skills`  
**同步方式**: git submodule  
**更新命令**: `bash scripts/update-matt-skills.sh`
