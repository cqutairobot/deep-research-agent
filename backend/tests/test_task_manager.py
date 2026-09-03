import time
import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock
from app.services.task_manager import TaskManager, TaskStatus

@pytest.mark.asyncio
async def test_task_creation_and_initial_status():
    """测试任务创建与初始状态"""
    manager = TaskManager()
    task_id = manager.create_task(
        user_query="测试研究任务",
        research_depth="standard",
        report_style="consulting",
        auto_approve_outline=True,
        max_iterations=2
    )
    assert task_id in manager.tasks
    task = manager.get_task(task_id)
    assert task is not None
    assert task["status"] == TaskStatus.PENDING
    assert task["state"]["user_query"] == "测试研究任务"

@pytest.mark.asyncio
async def test_cancel_task_lifecycle():
    """测试任务取消与防止重复取消 (Bug 2)"""
    manager = TaskManager()
    task_id = manager.create_task(
        user_query="测试取消任务",
        research_depth="standard",
        report_style="consulting",
        auto_approve_outline=False
    )
    task = manager.get_task(task_id)
    assert task is not None
    
    # 模拟处于等待审批状态
    task["status"] = TaskStatus.WAITING_OUTLINE_APPROVAL
    cancelled = manager.cancel_task(task_id)
    assert cancelled is True
    assert task["status"] == TaskStatus.CANCELLED

    # 对已经处于终态的任务再次取消应返回 False
    second_cancelled = manager.cancel_task(task_id)
    assert second_cancelled is False

@pytest.mark.asyncio
async def test_stream_event_replay_with_last_event_id():
    """测试断线重连与 Last-Event-ID 事件回放 (Bug 3)"""
    manager = TaskManager()
    task_id = manager.create_task(
        user_query="测试事件回放",
        research_depth="standard",
        report_style="consulting",
        auto_approve_outline=True
    )
    
    # 发送 3 个事件
    manager.emit_event(task_id, "thought", {"message": "正在规划大纲... (1)"})
    manager.emit_event(task_id, "thought", {"message": "正在检索资料... (2)"})
    manager.emit_event(task_id, "thought", {"message": "正在提炼事实... (3)"})

    # 从 last_event_id = 1 重连，第 1 个事件是 status 当前状态，随后应回放第 2、3 号事件
    received_events = []
    async for sse_item in manager.subscribe_stream(task_id, last_event_id="1"):
        received_events.append(sse_item)
        if len(received_events) >= 3:
            break

    assert len(received_events) == 3
    assert received_events[0].get("event") == "status"
    assert received_events[1].get("id") == "2"
    assert received_events[2].get("id") == "3"

@pytest.mark.asyncio
async def test_task_failed_event_emission():
    """测试任务发生异常时向前端发送 failed 终态事件 (Bug 1)"""
    manager = TaskManager()
    task_id = manager.create_task(
        user_query="测试异常捕获",
        research_depth="standard",
        report_style="consulting",
        auto_approve_outline=True
    )

    # 模拟在执行过程中抛出异常
    with patch("app.services.task_manager.plan_outline_node", side_effect=RuntimeError("模拟大模型超时崩溃")):
        await manager._run_task_lifecycle(task_id)

    task = manager.get_task(task_id)
    assert task is not None
    assert task["status"] == TaskStatus.FAILED
    assert "模拟大模型超时崩溃" in str(task.get("error"))

    # 检查流输出中包含 failed 事件
    stream_events = []
    async for sse_item in manager.subscribe_stream(task_id):
        stream_events.append(sse_item)

    failed_events = [e for e in stream_events if e.get("event") == "failed"]
    assert len(failed_events) == 1
    assert "模拟大模型超时崩溃" in failed_events[0].get("data", "")

@pytest.mark.asyncio
async def test_cleanup_expired_tasks():
    """测试过期任务与内存资源回收 (Bug 11)"""
    manager = TaskManager()
    task_id = manager.create_task(
        user_query="测试清理任务",
        research_depth="standard",
        report_style="consulting",
        auto_approve_outline=True
    )
    task = manager.get_task(task_id)
    assert task is not None
    task["status"] = TaskStatus.COMPLETED
    # 模拟任务更新时间已在 8000 秒前
    task["created_at"] = time.time() - 8000
    task["updated_at"] = time.time() - 8000

    cleaned = manager.cleanup_expired_tasks(max_age_seconds=7200)
    assert cleaned >= 1
    assert task_id not in manager.tasks
