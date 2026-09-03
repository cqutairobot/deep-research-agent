import asyncio
import json
import uuid
import time
from typing import Dict, Any, List, Optional, AsyncGenerator
from enum import Enum

from app.agents.state import ResearchState, ChapterOutline
from app.agents.planner import plan_outline_node
from app.agents.researcher import research_worker_node
from app.agents.critic import critic_node
from app.agents.writer import synthesize_report_node
from app.agents.verifier import citation_verifier_node

class TaskStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    WAITING_OUTLINE_APPROVAL = "waiting_outline_approval"
    RESEARCHING = "researching"
    WRITING = "writing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"

class TaskManager:
    """
    异步调研任务生命周期与 SSE 事件流广播调度管理器 (包含历史回放、取消防竞态与 TTL 清理)
    """
    
    def __init__(self, event_history_limit: int = 100, task_ttl_seconds: int = 7200):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.subscribers: Dict[str, List[asyncio.Queue]] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.approval_events: Dict[str, asyncio.Event] = {}
        self.approved_outlines: Dict[str, List[ChapterOutline]] = {}
        self.event_history: Dict[str, List[Dict[str, Any]]] = {}
        self.event_seq_counters: Dict[str, int] = {}
        self.event_history_limit = event_history_limit
        self.task_ttl_seconds = task_ttl_seconds

    def create_task(
        self,
        user_query: str,
        research_depth: str = "standard",
        report_style: str = "consulting",
        auto_approve_outline: bool = True,
        max_iterations: int = 2,
        local_documents: Optional[List[Dict[str, Any]]] = None,
        owner_id: Optional[str] = None
    ) -> str:
        """创建异步调研任务并启动后台调度"""
        self.cleanup_expired_tasks()
        
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        max_iter = 1 if research_depth == "quick" else (3 if research_depth == "deep" else max_iterations)
        docs = local_documents or []
        
        state: ResearchState = {
            "task_id": task_id,
            "user_query": user_query,
            "research_depth": research_depth,
            "report_style": report_style,
            "clarification": "",
            "outline": [],
            "citations": [],
            "current_step": "plan",
            "local_documents": docs,
            "iteration_count": 1,
            "max_iterations": max_iter,
            "critic_feedback": "",
            "needs_more_research": False,
            "draft_report": "",
            "final_report": "",
            "logs": [f"任务初始化成功，课题: {user_query} (本地私有文档: {len(docs)} 份)"]
        }
        
        self.tasks[task_id] = {
            "task_id": task_id,
            "status": TaskStatus.PENDING,
            "created_at": time.time(),
            "updated_at": time.time(),
            "auto_approve_outline": auto_approve_outline,
            "state": state,
            "error": None,
            "owner_id": owner_id
        }
        
        self.subscribers[task_id] = []
        self.approval_events[task_id] = asyncio.Event()
        self.event_history[task_id] = []
        self.event_seq_counters[task_id] = 0
        
        async_task = asyncio.create_task(self._run_task_lifecycle(task_id))
        self.running_tasks[task_id] = async_task
        
        return task_id

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.tasks.get(task_id)

    def list_tasks(self) -> List[Dict[str, Any]]:
        return list(self.tasks.values())

    def approve_outline(self, task_id: str, approved_outline: List[ChapterOutline]) -> bool:
        if task_id not in self.tasks:
            return False
            
        task_info = self.tasks[task_id]
        if task_info["status"] != TaskStatus.WAITING_OUTLINE_APPROVAL:
            return False
            
        self.approved_outlines[task_id] = approved_outline
        if task_id in self.approval_events:
            self.approval_events[task_id].set()
        return True

    def cancel_task(self, task_id: str) -> bool:
        if task_id not in self.tasks:
            return False
            
        task_info = self.tasks[task_id]
        # 终态不可再次取消 (Bug 2)
        if task_info["status"] in [TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED]:
            return False
            
        task_info["status"] = TaskStatus.CANCELLED
        task_info["updated_at"] = time.time()
        
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            
        if task_id in self.approval_events:
            self.approval_events[task_id].set()
            
        self._emit_event(task_id, "cancelled", {"message": "任务已由用户主动取消"})
        self._cleanup_terminal_resources(task_id)
        return True

    def _emit_event(self, task_id: str, event_type: str, data: Any):
        if task_id in self.tasks:
            self.tasks[task_id]["updated_at"] = time.time()
            
        seq_id = self.event_seq_counters.get(task_id, 0) + 1
        self.event_seq_counters[task_id] = seq_id
        
        payload = {
            "id": str(seq_id),
            "event": event_type,
            "data": json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data
        }
        
        # 维护有上限的事件历史 (Bug 3)
        history = self.event_history.setdefault(task_id, [])
        history.append(payload)
        if len(history) > self.event_history_limit:
            self.event_history[task_id] = history[-self.event_history_limit:]
        
        for queue in self.subscribers.get(task_id, []):
            try:
                queue.put_nowait(payload)
            except Exception:
                pass

    def _cleanup_terminal_resources(self, task_id: str):
        """清理终态临时对象 (Bug 11)"""
        self.running_tasks.pop(task_id, None)
        self.approval_events.pop(task_id, None)
        self.approved_outlines.pop(task_id, None)

    def emit_event(self, task_id: str, event_type: str, data: Any):
        """发送流式事件公共入口 (Bug 3)"""
        return self._emit_event(task_id, event_type, data)

    def cleanup_expired_tasks(self, max_age_seconds: Optional[int] = None) -> int:
        """清理超过 TTL 时限的旧任务 (Bug 11)"""
        now = time.time()
        ttl = max_age_seconds if max_age_seconds is not None else self.task_ttl_seconds
        expired_ids = [
            tid for tid, t in self.tasks.items()
            if t["status"] in [TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED]
            and now - t.get("updated_at", t.get("created_at", now)) > ttl
        ]
        for tid in expired_ids:
            self.tasks.pop(tid, None)
            self.subscribers.pop(tid, None)
            self.event_history.pop(tid, None)
            self.event_seq_counters.pop(tid, None)
            self._cleanup_terminal_resources(tid)
        return len(expired_ids)

    async def subscribe_stream(self, task_id: str, last_event_id: Optional[str] = None) -> AsyncGenerator[Dict[str, str], None]:
        if task_id not in self.tasks:
            yield {
                "event": "error",
                "data": json.dumps({"error": "任务不存在"}, ensure_ascii=False)
            }
            return

        task_info = self.tasks[task_id]
        status = task_info["status"]

        # 如果任务已经处于终态且没有传入 last_event_id，直接补发状态与终态事件后结束 (Bug 1, Bug 3)
        if status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED]:
            yield {
                "event": "status",
                "data": json.dumps({
                    "task_id": task_id,
                    "status": task_info["status"],
                    "state": task_info["state"]
                }, ensure_ascii=False)
            }
            # 回放历史或终态
            for event in self.event_history.get(task_id, []):
                yield event
            return

        queue = asyncio.Queue()
        self.subscribers.setdefault(task_id, []).append(queue)
        
        # 发送当前状态
        yield {
            "event": "status",
            "data": json.dumps({
                "task_id": task_id,
                "status": task_info["status"],
                "state": task_info["state"]
            }, ensure_ascii=False)
        }
        
        # 补发错过的历史事件 (支持首次连接无 last_event_id 时全量补发，或断线重连带 last_event_id 时增量补发)
        last_seq = 0
        if last_event_id is not None:
            try:
                last_seq = int(last_event_id)
            except ValueError:
                last_seq = 0
        for event in self.event_history.get(task_id, []):
            if int(event.get("id", 0)) > last_seq:
                yield event
        
        try:
            while True:
                payload = await queue.get()
                yield payload
                if payload["event"] in ["completed", "cancelled", "failed"]:
                    break
        finally:
            if task_id in self.subscribers and queue in self.subscribers[task_id]:
                self.subscribers[task_id].remove(queue)

    def _is_task_cancelled(self, task_id: str) -> bool:
        if task_id not in self.tasks:
            return True
        return self.tasks[task_id]["status"] == TaskStatus.CANCELLED

    async def _run_task_lifecycle(self, task_id: str):
        task_info = self.tasks[task_id]
        state: ResearchState = task_info["state"]
        auto_approve = task_info["auto_approve_outline"]
        
        try:
            if self._is_task_cancelled(task_id):
                return

            # 1. Planner 规划阶段
            task_info["status"] = TaskStatus.PLANNING
            self._emit_event(task_id, "thought", {"step": "planner", "message": "正在调用大模型拆解课题并规划大纲..."})
            
            plan_res = await asyncio.to_thread(plan_outline_node, state)
            if self._is_task_cancelled(task_id):
                return
            state.update(plan_res)
            
            self._emit_event(task_id, "outline_ready", {
                "clarification": state.get("clarification"),
                "outline": state.get("outline")
            })
            
            # 2. 人机协同大纲确认挂起
            if not auto_approve:
                task_info["status"] = TaskStatus.WAITING_OUTLINE_APPROVAL
                self._emit_event(task_id, "waiting_approval", {"message": "大纲已生成，等待人工确认或修改..."})
                
                await self.approval_events[task_id].wait()
                if self._is_task_cancelled(task_id):
                    return
                
                if task_id in self.approved_outlines:
                    state["outline"] = self.approved_outlines[task_id]
                    self._emit_event(task_id, "thought", {"step": "approved", "message": "大纲已由人工确认通过！"})

            # 3. 检索与 Critic 反思循环阶段
            if self._is_task_cancelled(task_id):
                return
            task_info["status"] = TaskStatus.RESEARCHING
            max_iter = state.get("max_iterations", 2)
            
            while True:
                if self._is_task_cancelled(task_id):
                    return
                current_iter = state.get("iteration_count", 1)
                self._emit_event(task_id, "search", {
                    "iteration": current_iter,
                    "max_iterations": max_iter,
                    "message": f"正在执行第 {current_iter}/{max_iter} 轮全网检索与混合知识提炼..."
                })
                
                def on_research_progress(evt_name: str, payload: Any):
                    self._emit_event(task_id, evt_name, payload)

                res_data = await asyncio.to_thread(research_worker_node, state, on_progress=on_research_progress)
                if self._is_task_cancelled(task_id):
                    return
                state.update(res_data)
                
                self._emit_event(task_id, "facts_extracted", {
                    "total_citations": len(state.get("citations", [])),
                    "citations": state.get("citations", []),
                    "outline": state.get("outline", [])
                })
                
                # Critic 评估节点
                self._emit_event(task_id, "thought", {"step": "critic", "message": "Critic 正在评估事实充实度与矛盾核验..."})
                critic_data = await asyncio.to_thread(critic_node, state)
                if self._is_task_cancelled(task_id):
                    return
                state.update(critic_data)
                
                self._emit_event(task_id, "critic_evaluated", {
                    "feedback": state.get("critic_feedback"),
                    "needs_more_research": state.get("needs_more_research"),
                    "iteration": state.get("iteration_count")
                })
                
                if not state.get("needs_more_research", False) or state.get("iteration_count", 1) > max_iter:
                    break

            # 4. Writer 撰写研报初稿阶段
            if self._is_task_cancelled(task_id):
                return
            task_info["status"] = TaskStatus.WRITING
            self._emit_event(task_id, "thought", {"step": "writer", "message": "Writer 正在根据多轮事实撰写深度研报..."})
            
            writer_res = await asyncio.to_thread(synthesize_report_node, state)
            if self._is_task_cancelled(task_id):
                return
            state.update(writer_res)
            
            # 5. Verifier 引用防幻觉校验阶段
            task_info["status"] = TaskStatus.VERIFYING
            self._emit_event(task_id, "thought", {"step": "verifier", "message": "Verifier 正在进行引用溯源 1:1 严格校验与防幻觉修正..."})
            
            verifier_res = await asyncio.to_thread(citation_verifier_node, state)
            if self._is_task_cancelled(task_id):
                return
            state.update(verifier_res)
            
            # 6. 完成任务并持久化归档至 SQLite (Phase 4 升级)
            task_info["status"] = TaskStatus.COMPLETED
            
            try:
                from app.db.sqlite_store import save_report_archive
                save_report_archive(
                    task_id=task_id,
                    user_query=state.get("user_query", ""),
                    research_depth=state.get("research_depth", "standard"),
                    report_style=state.get("report_style", "consulting"),
                    final_report=state.get("final_report", ""),
                    outline=state.get("outline", []),
                    citations=state.get("citations", []),
                    summary=state.get("clarification", "")
                )
            except Exception as archive_err:
                print(f"[Archive Warning] 自动归档任务 {task_id} 失败: {archive_err}")

            self._emit_event(task_id, "completed", {
                "task_id": task_id,
                "final_report": state.get("final_report"),
                "citations": state.get("citations"),
                "outline": state.get("outline")
            })
            self._cleanup_terminal_resources(task_id)

        except asyncio.CancelledError:
            task_info["status"] = TaskStatus.CANCELLED
            self._emit_event(task_id, "cancelled", {"message": "任务已取消"})
            self._cleanup_terminal_resources(task_id)
        except Exception as e:
            task_info["status"] = TaskStatus.FAILED
            task_info["error"] = str(e)
            # 统一失败终态事件，附带 error 字段 (Bug 1)
            self._emit_event(task_id, "failed", {"error": str(e), "message": f"任务执行失败: {str(e)}"})
            self._cleanup_terminal_resources(task_id)

task_manager = TaskManager()
