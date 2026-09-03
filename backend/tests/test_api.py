import pytest
import asyncio
import json
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.task_manager import task_manager, TaskStatus

@pytest.mark.asyncio
async def test_health_check():
    """测试服务健康检查端点"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data

@pytest.mark.asyncio
async def test_create_and_query_task():
    """测试任务创建与详情查询接口"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "query": "固态电池最新突破",
            "depth": "quick",
            "style": "consulting",
            "auto_approve_outline": True,
            "max_iterations": 1
        }
        create_resp = await ac.post("/api/v1/research/tasks", json=payload)
        assert create_resp.status_code == 201
        created_data = create_resp.json()
        assert "task_id" in created_data
        task_id = created_data["task_id"]
        
        # 查询任务详情
        detail_resp = await ac.get(f"/api/v1/research/tasks/{task_id}")
        assert detail_resp.status_code == 200
        task_detail = detail_resp.json()
        assert task_detail["task_id"] == task_id
        valid_statuses = [s.value for s in TaskStatus]
        assert task_detail["status"] in valid_statuses

@pytest.mark.asyncio
async def test_get_nonexistent_task_404():
    """测试查询不存在任务返回 404"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/research/tasks/task_invalid_9999")
        assert resp.status_code == 404
        assert "不存在" in resp.json()["detail"]

@pytest.mark.asyncio
async def test_cancel_task():
    """测试取消任务接口"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create_resp = await ac.post("/api/v1/research/tasks", json={"query": "测试取消流程"})
        task_id = create_resp.json()["task_id"]
        
        cancel_resp = await ac.post(f"/api/v1/research/tasks/{task_id}/cancel")
        assert cancel_resp.status_code == 200
        
        # 验证任务已被取消
        detail_resp = await ac.get(f"/api/v1/research/tasks/{task_id}")
        assert detail_resp.json()["status"] == TaskStatus.CANCELLED.value

@pytest.mark.asyncio
async def test_human_in_the_loop_approval_api():
    """测试人机协同大纲审批接口契约与有效载荷"""
    task_id = task_manager.create_task(
        user_query="测试审批API",
        research_depth="standard",
        report_style="consulting",
        auto_approve_outline=False
    )
    task = task_manager.get_task(task_id)
    assert task is not None
    task["status"] = TaskStatus.WAITING_OUTLINE_APPROVAL
    
    # 提交审批修改后的大纲
    approved_payload = {
        "outline": [
            {
                "chapter_num": 1,
                "title": "人工审核后的核心章节",
                "focus": "聚焦实际落地数据",
                "search_queries": ["测试检索词 1"],
                "extracted_facts": []
            }
        ]
    }
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(f"/api/v1/research/tasks/{task_id}/approve_outline", json=approved_payload)
        assert resp.status_code == 200
        assert "大纲已确认" in resp.json()["message"]

@pytest.mark.asyncio
async def test_outline_validation_empty_error():
    """测试提交非法/空大纲时触发 Pydantic 校验拒绝 (Bug 20)"""
    task_id = task_manager.create_task(
        user_query="测试非法大纲",
        research_depth="standard",
        report_style="consulting",
        auto_approve_outline=False
    )
    task = task_manager.get_task(task_id)
    assert task is not None
    task["status"] = TaskStatus.WAITING_OUTLINE_APPROVAL

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 空章节数组
        resp1 = await ac.post(f"/api/v1/research/tasks/{task_id}/approve_outline", json={"outline": []})
        assert resp1.status_code == 422

        # 章节标题为空白
        resp2 = await ac.post(f"/api/v1/research/tasks/{task_id}/approve_outline", json={
            "outline": [{"chapter_num": 1, "title": "  ", "focus": "有效聚焦"}]
        })
        assert resp2.status_code == 422

@pytest.mark.asyncio
async def test_sse_stream_generator():
    """测试 TaskManager 核心 SSE 事件流传输与回放"""
    task_id = task_manager.create_task(
        user_query="测试流式生成",
        research_depth="quick",
        report_style="consulting",
        auto_approve_outline=True
    )
    
    task_manager.emit_event(task_id, "thought", {"message": "正在规划大纲..."})
    
    events = []
    async for sse_item in task_manager.subscribe_stream(task_id):
        events.append(sse_item)
        if len(events) >= 2:
            break

    assert len(events) >= 2
    assert events[0]["event"] == "status"
    assert events[1]["event"] == "thought"
