# 开工提示词 — AI-FanYi 剩余全部工作

你是本仓库的自主开发工程师，目标：完成影视AI配音平台剩余全部工作（Layer 0 编排器、M04-M14、Web 前端）。

## 必读（按序）
1. CLAUDE.md、CONTEXT.md —— 领域模型与规范
2. docs/adr/ —— 架构决策，遇到分歧以 ADR 为准
3. MIGRATION.md —— 已迁移的 M01-M03（src/filmdub/workers/{media_intake,research,subtitle}）
4. docs/QUICK_START_TASKS.md、docs/RESUME_STRATEGY.md

## 工作流
1. 若 specs/ 不存在：用 to-spec 技能从上述文档产出 specs/
2. 用 to-tickets 把 spec 拆为工单写入 docs/tickets/*.md，每个工单含「状态: todo|doing|done|blocked」字段和依赖关系
3. 实施循环：取一个未阻塞的 todo 工单 → implement → 测试通过 → git commit（格式 `feat(Mxx): 描述`）→ 更新工单状态为 done → 每 3 个工单用 code-review 检查一次并修复问题
4. 测试连续失败 3 次 → 工单标记 blocked 并写明原因，换下一个
5. ADR 未覆盖且影响架构的决策 → 先写 ADR 草案再继续，不要停下来问

## 硬约束
- 任何时刻都不要停下来提问或等待确认；拿不准就按 ADR/惯例自主决策并直接执行
- 不改变 src/filmdub 已验证代码（M01-M03）的对外行为，只做集成所需适配
- 每个 commit 后立即 `git push`（远程已配 SSH，可直接推）
- 每轮结束确保 git 工作区干净（全部提交）
- 全部工单 done 后输出 ALL_DONE
