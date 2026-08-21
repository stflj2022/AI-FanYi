新会话冷启动。旧会话上下文已满被丢弃，所有真实状态都在磁盘上，按序恢复：

1. 读 CLAUDE.md、CONTEXT.md（领域规范）
2. 读 docs/UNATTENDED_SETUP.md（本系统说明）
3. 读 specs/ 全部规格文档
4. 读 docs/tickets/*.md 工单及各自状态
5. git log --oneline -30 看已完成工作；git status 看未提交内容（若有半成品：能续则续，不能续则回滚该工单为 todo）

然后继续 KICKOFF.md 定义的工作流：领一张未阻塞 todo 工单 → implement → 测试通过 → git commit → push → 更新工单状态。全部工单 done 后只输出 ALL_DONE。
