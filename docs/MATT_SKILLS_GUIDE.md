# Matt 技能使用指南

本指南介绍如何在 AI-FanYi 项目中使用 Matt Pocock 的工程技能。

## ✅ 配置状态

- [x] CLAUDE.md - 已更新，包含完整的 Agent Skills 部分
- [x] docs/agents/issue-tracker.md - GitHub Issues 配置
- [x] docs/agents/triage-labels.md - 分流标签配置
- [x] docs/agents/domain.md - 领域文档配置
- [x] CONTEXT.md - 领域模型文档

## 🎯 核心开发流程

### 1. 质询阶段 (Grill)

在开始编写代码前，先通过质询澄清设计细节。

```bash
# 基础质询
/grill-me

# 质询并生成文档（ADR、术语表等）
/grill-with-docs
```

**AI 会问的问题类型**：
- 这个模块的核心目标是什么？
- 输入输出是什么格式？
- 与其他模块的交互方式？
- 边界情况如何处理？
- 错误处理策略？
- 性能要求？
- 测试策略？

**建议**：大部分情况下直接采纳 AI 的建议即可。

### 2. 规范生成 (to-spec)

对于较大的任务，生成详细的规范文档。

```bash
/to-spec
```

**输出**：
- 在 `docs/agents/` 或 GitHub Issues 中创建规范文档
- 包含模块目标、接口设计、数据模型、测试要求等

**适用场景**：
- 新增一个完整的模块（如 M04）
- 大型重构任务
- 跨多个模块的功能开发

**不适用场景**：
- 小型 bug 修复
- 简单的功能增强
- 文档更新

### 3. 任务分解 (to-tickets)

将规范分解为具体可执行的任务。

```bash
/to-tickets
```

**输出**：
- 创建一系列 tracer-bullet tickets
- 每个任务声明其依赖关系（blocked-by）
- 任务按依赖顺序排列

**示例输出**：
```
ticket-001: 创建数据库模型
  blocked-by: none

ticket-002: 实现 Character DB API
  blocked-by: ticket-001

ticket-003: 编写单元测试
  blocked-by: ticket-002
```

### 4. 执行实现 (implement)

根据规范和任务列表执行实现。

```bash
/implement
```

**自动执行流程**：
1. 检查未被阻塞的任务
2. 立即执行第一个可用任务
3. 任务完成后，自动解锁后续任务
4. 继续执行下一个可用任务
5. 循环直到所有任务完成
6. 最后自动运行 `/code-review`

**特点**：
- 自动处理任务依赖关系
- 使用 TDD 开发（在预定的边界）
- 定期运行类型检查和测试
- 完成后自动提交到当前分支

### 5. 代码审查 (code-review)

对代码进行双轴审查。

```bash
# 审查从 main 到当前分支的变更
/code-review main

# 审查从某个 commit 到当前分支的变更
/code-review abc123

# 审查最近 5 个提交
/code-review HEAD~5
```

**双轴审查**：
- **Standards 轴**：代码是否遵循项目的编码规范？
- **Spec 轴**：代码是否忠实实现了原始规范？

**并行执行**：两个轴由独立的 sub-agent 并行执行，避免上下文污染。

**12 种 Code Bad Smells 检查**：
1. Duplicated Code - 重复代码
2. Long Method - 过长的方法
3. Large Class - 过大的类
4. Long Parameter List - 过长的参数列表
5. Divergent Change - 发散式变更
6. Shotgun Surgery - 霰弹式修改
7. Feature Envy - 依恋情结
8. Data Clumps - 数据泥团
9. Primitive Obsession - 基本类型偏执
10. Switch Statements - switch 语句
11. Temporary Field - 临时字段
12. Refused Bequest - 被拒绝的遗赠

## 📋 完整开发示例

### 示例 1: 开发 Module 04 (Character Database)

```bash
cd /home/wu/桌面/AI-FanYi

# === 阶段 1: 质询 ===
/grill-me

# AI 会问你：
# - Character Database 的核心职责是什么？
# - 与 Module 02 的 Character DB 有何区别？
# - 需要哪些核心表？
# - 如何处理人物关系的持久化？
# - 迁移策略是什么？
# - API 接口设计？

# === 阶段 2: 生成规范（大任务）===
/to-spec

# 生成 docs/agents/specs/m04-character-db.md

# === 阶段 3: 分解任务 ===
/to-tickets

# 创建任务列表：
# - [ ] ticket-001: 设计数据库 schema
# - [ ] ticket-002: 实现 ORM 模型
# - [ ] ticket-003: 实现 CRUD API
# - [ ] ticket-004: 编写单元测试
# - [ ] ticket-005: 编写集成测试

# === 阶段 4: 执行 ===
/implement

# 自动：
# 1. 检测 ticket-001 未被阻塞 → 执行
# 2. 完成 ticket-001 → 解锁 ticket-002
# 3. 检测 ticket-002 未被阻塞 → 执行
# 4. ...
# 5. 所有任务完成后，自动运行 /code-review

# === 阶段 5: 审查 ===
/code-review main

# 查看审查结果，修复问题后再次提交
```

### 示例 2: 修复 Bug

```bash
# 小任务可以跳过 to-spec 和 to-tickets

# === 阶段 1: 质询 ===
/grill-me

# AI 问：
# - Bug 的具体表现是什么？
# - 能否复现？复现步骤是什么？
# - 预期行为是什么？
# - 可能的原因是什么？

# === 阶段 2: 直接实现 ===
/implement

# AI 会：
# 1. 分析问题
# 2. 编写修复
# 3. 编写测试
# 4. 运行测试
# 5. 提交代码

# === 阶段 3: 审查 ===
/code-review HEAD~1
```

### 示例 3: 重构代码

```bash
# === 阶段 1: 质询 ===
/grill-me

# AI 问：
# - 为什么要重构？
# - 重构的目标是什么？
# - 哪些部分需要重构？
# - 如何保证重构不破坏功能？

# === 阶段 2: 规范（可选）===
/to-spec  # 如果重构规模较大

# === 阶段 3: 分解任务（可选）===
/to-tickets  # 如果涉及多个模块

# === 阶段 4: 执行 ===
/implement

# === 阶段 5: 审查 ===
/code-review main
```

## 🛠️ 其他有用技能

### domain-modeling

领域建模，用于定义和优化项目的领域模型。

```bash
/domain-modeling
```

**用途**：
- 定义核心概念和术语
- 创建或更新 CONTEXT.md
- 记录架构决策（ADR）
- 建立概念之间的关系

### research

研究任务，用于收集信息。

```bash
/research
```

**用途**：
- 研究某个技术方案
- 调研最佳实践
- 收集 API 文档
- 分析竞品

### prototype

快速原型验证。

```bash
/prototype
```

**用途**：
- 验证设计想法
- 测试技术可行性
- 探索 API 设计
- 快速 UI 原型

### tdd

测试驱动开发。

```bash
/tdd
```

**用途**：
- 编写测试先行
- 红绿重构循环
- 保证代码质量

### diagnosing-bugs

Bug 诊断。

```bash
/diagnosing-bugs
```

**用途**：
- 分析复杂 bug
- 找出根本原因
- 提供修复建议

## 📊 配置文件说明

### CLAUDE.md

项目级 Agent 配置，包含：
- Agent Skills 部分
- 项目描述
- 系统架构
- 模块列表
- 开发流程

### docs/agents/issue-tracker.md

问题追踪器配置，指定：
- 使用 GitHub Issues
- 仓库地址：stflj2022/-PDF-
- CLI 工具：gh
- Issue 结构和标签规范

### docs/agents/triage-labels.md

分流标签映射，定义 5 个标准标签：
- `needs-triage` - 需要初步审查
- `needs-info` - 需要更多信息
- `ready-for-agent` - 可以由 AI 处理
- `ready-for-human` - 需要人工处理
- `wontfix` - 不会处理

### docs/agents/domain.md

领域文档配置，指定：
- 单上下文布局（single-context）
- CONTEXT.md 位置和内容
- ADRs 存储位置（docs/adr/）
- 核心领域概念

### CONTEXT.md

领域模型文档，包含：
- 系统概述
- 核心概念定义
- 模块说明
- 数据流
- 长期资产

## 🎓 最佳实践

1. **大任务用完整流程**：对于新增模块、大型重构，使用完整流程
2. **小任务简化**：对于 bug 修复、小功能，直接 grill + implement
3. **定期审查**：每次提交后运行 code-review
4. **保持文档更新**：使用 domain-modeling 保持 CONTEXT.md 同步
5. **利用 TDD**：在 implement 中自动使用 TDD 开发

## 📖 参考资源

- Matt Pocock 的工程技能集
- pi-coding-agent 文档
- 项目架构设计文档（docs/DESIGN_INDEX.md）
- 架构决策记录（docs/adr/）

## ❓ 常见问题

### Q: 什么时候需要用 to-spec？

A: 当任务规模较大、涉及多个模块、或者需要详细设计文档时使用。小任务（如 bug 修复、简单功能）可以跳过。

### Q: to-tickets 生成的任务会自动执行吗？

A: 不会。需要运行 `/implement` 来执行任务。implement 会自动处理依赖关系。

### Q: code-review 会修改代码吗？

A: 不会。code-review 只是审查并给出建议，需要手动修改代码。

### Q: 如果 implement 执行失败怎么办？

A: implement 会显示错误信息，修复问题后可以再次运行。它会从上次失败的地方继续。

### Q: 如何查看当前有哪些技能可用？

A: 在 pi 中输入 `/help` 或查看 `~/.pi/agent/skills/` 目录。

## 🚀 快速开始

现在你可以在 AI-FanYi 项目中使用 Matt 技能了：

```bash
cd /home/wu/桌面/AI-FanYi

# 开始你的第一个任务
/grill-me
```

祝你开发愉快！🎉
