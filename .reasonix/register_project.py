"""把已完成的 laobai 项目注册到 orchestrator.db，使其显示在 Web UI。"""
import asyncio
import sys
import pathlib

sys.path.insert(0, "/home/wu/桌面/AI-FanYi/src")
PROJECT_ID = "proj_64007428ffb6"


async def main():
    import uuid
    from filmdub.orchestrator.database import AsyncSessionLocal, init_db
    from filmdub.orchestrator.models import Project, ProjectStatus, Job, JobStatus
    from sqlalchemy import select

    await init_db()
    async with AsyncSessionLocal() as session:
        existing = (await session.execute(select(Project).where(Project.name == "laobai E2E 完整流程"))).scalar_one_or_none()
        if existing:
            print("项目已存在，跳过")
            return
        # orchestrator 的主键是 UUID；这里为 laobai 流程单独建一条记录
        pid = uuid.uuid4()
        p = Project(
            id=pid,
            name="laobai E2E 完整流程",
            description="laobai.mp4 Layer0+M01~M14 完整配音流程，QA=100（流程项目: proj_64007428ffb6）",
            status=ProjectStatus.COMPLETED,
            media_type="video",
            title="老白测试片段",
            original_language="en",
            target_language="zh-CN",
        )
        session.add(p)
        await session.commit()
        print("已注册项目(id=%s)" % pid)

        # 同步记录 14 个 Job（便于 Web UI 查看模块状态）
        modules = ["M01","M02","M03","M04","M05","M06","M07","M08","M09","M10","M11","M12","M13","M14"]
        for m in modules:
            session.add(Job(project_id=pid, name=f"{m}-laobai", module_id=m, status=JobStatus.COMPLETED))
        await session.commit()
        print("已写入 14 个 Job")


if __name__ == "__main__":
    asyncio.run(main())
