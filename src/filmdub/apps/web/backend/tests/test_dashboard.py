"""Dashboard 相关 API 测试"""
import pytest
from httpx import AsyncClient


class TestDashboardAPI:
    """Dashboard API 测试"""

    @pytest.mark.asyncio
    async def test_get_job_stats_empty(self, async_client: AsyncClient, auth_headers):
        """测试获取空任务统计"""
        response = await async_client.get(
            "/api/v1/jobs/stats",
            headers=auth_headers,
        )

        # 打印错误信息
        if response.status_code != 200:
            print(f"Error response: {response.text}")

        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert "pending" in data
        assert "running" in data
        assert "completed" in data
        assert "failed" in data
        assert "active" in data
        assert "finished" in data

        # 空状态下所有计数应为 0
        assert data["total"] == 0
        assert data["active"] == 0
        assert data["finished"] == 0

    @pytest.mark.asyncio
    async def test_get_recent_jobs_empty(self, async_client: AsyncClient, auth_headers):
        """测试获取空最近任务列表"""
        response = await async_client.get(
            "/api/v1/jobs/recent",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) == 0

    @pytest.mark.asyncio
    async def test_get_job_stats_with_jobs(
        self, async_client: AsyncClient, auth_headers, test_project
    ):
        """测试获取有任务时的统计"""
        from filmdub.core.models import Job

        # 创建测试任务
        async with async_client.app.state.db() as db:
            jobs = [
                Job(
                    project_id=test_project.id,
                    name=f"测试任务 {i}",
                    status=status,
                )
                for i, status in enumerate(["pending", "running", "completed", "failed"])
            ]
            db.add_all(jobs)
            await db.commit()

        try:
            response = await async_client.get(
                "/api/v1/jobs/stats",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            assert data["total"] == 4
            assert data["pending"] == 1
            assert data["running"] == 1
            assert data["completed"] == 1
            assert data["failed"] == 1
            assert data["active"] == 1  # running
            assert data["finished"] == 2  # completed + failed
        finally:
            # 清理
            async with async_client.app.state.db() as db:
                for job in jobs:
                    await db.delete(job)
                await db.commit()

    @pytest.mark.asyncio
    async def test_get_recent_jobs_with_jobs(
        self, async_client: AsyncClient, auth_headers, test_project
    ):
        """测试获取有任务时的最近任务"""
        from filmdub.core.models import Job

        # 创建测试任务
        async with async_client.app.state.db() as db:
            jobs = [
                Job(
                    project_id=test_project.id,
                    name=f"测试任务 {i}",
                    status="pending",
                )
                for i in range(5)
            ]
            db.add_all(jobs)
            await db.commit()

        try:
            response = await async_client.get(
                "/api/v1/jobs/recent",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            assert "items" in data
            assert isinstance(data["items"], list)
            assert len(data["items"]) == 5

            # 验证每个任务都有必要字段
            for item in data["items"]:
                assert "id" in item
                assert "name" in item
                assert "status" in item
                assert "created_at" in item
        finally:
            # 清理
            async with async_client.app.state.db() as db:
                for job in jobs:
                    await db.delete(job)
                await db.commit()

    @pytest.mark.asyncio
    async def test_get_recent_jobs_limit(self, async_client: AsyncClient, auth_headers, test_project):
        """测试最近任务数量限制"""
        from filmdub.core.models import Job

        # 创建更多任务
        async with async_client.app.state.db() as db:
            jobs = [
                Job(
                    project_id=test_project.id,
                    name=f"测试任务 {i}",
                    status="pending",
                )
                for i in range(15)
            ]
            db.add_all(jobs)
            await db.commit()

        try:
            # 默认限制 10 个
            response = await async_client.get(
                "/api/v1/jobs/recent",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) <= 10

            # 自定义限制为 5
            response = await async_client.get(
                "/api/v1/jobs/recent?limit=5",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 5
        finally:
            # 清理
            async with async_client.app.state.db() as db:
                for job in jobs:
                    await db.delete(job)
                await db.commit()

    @pytest.mark.asyncio
    async def test_get_recent_jobs_unauthorized(self, async_client: AsyncClient):
        """测试未授权访问最近任务"""
        response = await async_client.get("/api/v1/jobs/recent")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_job_stats_unauthorized(self, async_client: AsyncClient):
        """测试未授权访问统计信息"""
        response = await async_client.get("/api/v1/jobs/stats")

        assert response.status_code == 401
