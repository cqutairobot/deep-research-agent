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
    异步调研任务生命周期与 SSE 事件流广播调度管理器 (Phase 5 混合 RAG 版)
    """
    
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.subscribers: Dict[str, List[asyncio.Queue]] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.approval_events: Dict[str, asyncio.Event] = {}
        self.approved_outlines: Dict[str, List[ChapterOutline]] = {}

    def create_task(
        self,
        user_query: str,
        research_depth: str = "standard",
        report_style: str = "consulting",
        auto_approve_outline: bool = True,
        max_iterations: int = 2,
        local_documents: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """创建异步调研任务并启动后台调度"""
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
            "error": None
        }
        
        self.subscribers[task_id] = []
        self.approval_events[task_id] = asyncio.Event()
        
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
        self.approval_events[task_id].set()
        return True

    def cancel_task(self, task_id: str) -> bool:
        if task_id not in self.tasks:
            return False
            
        task_info = self.tasks[task_id]
        task_info["status"] = TaskStatus.CANCELLED
        task_info["updated_at"] = time.time()
        
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            
        self._emit_event(task_id, "cancelled", {"message": "任务已由用户主动取消"})
        return True

    def _emit_event(self, task_id: str, event_type: str, data: Any):
        if task_id in self.tasks:
            self.tasks[task_id]["updated_at"] = time.time()
            
        payload = {
            "event": event_type,
            "data": json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data
        }
        
        for queue in self.subscribers.get(task_id, []):
            try:
                queue.put_nowait(payload)
            except Exception:
                pass

    async def subscribe_stream(self, task_id: str) -> AsyncGenerator[Dict[str, str], None]:
        if task_id not in self.tasks:
            yield {
                "event": "error",
                "data": json.dumps({"error": "任务不存在"}, ensure_ascii=False)
            }
            return

        queue = asyncio.Queue()
        self.subscribers[task_id].append(queue)
        
        task_info = self.tasks[task_id]
        yield {
            "event": "status",
            "data": json.dumps({
                "task_id": task_id,
                "status": task_info["status"],
                "state": task_info["state"]
            }, ensure_ascii=False)
        }
        
        try:
            while True:
                payload = await queue.get()
                yield payload
                if payload["event"] in ["completed", "cancelled", "failed"]:
                    break
        finally:
            if task_id in self.subscribers and queue in self.subscribers[task_id]:
                self.subscribers[task_id].remove(queue)

    async def _run_task_lifecycle(self, task_id: str):
        task_info = self.tasks[task_id]
        state: ResearchState = task_info["state"]
        auto_approve = task_info["auto_approve_outline"]
        
        try:
            # 1. Planner 规划阶段
            task_info["status"] = TaskStatus.PLANNING
            self._emit_event(task_id, "thought", {"step": "planner", "message": "正在调用大模型拆解课题并规划大纲..."})
            
            plan_res = await asyncio.to_thread(plan_outline_node, state)
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
                
                if task_id in self.approved_outlines:
                    state["outline"] = self.approved_outlines[task_id]
                    self._emit_event(task_id, "thought", {"step": "approved", "message": "大纲已由人工确认通过！"})

            # 3. 检索与 Critic 反思循环阶段
            task_info["status"] = TaskStatus.RESEARCHING
            max_iter = state.get("max_iterations", 2)
            
            while True:
                current_iter = state.get("iteration_count", 1)
                self._emit_event(task_id, "search", {
                    "iteration": current_iter,
                    "max_iterations": max_iter,
                    "message": f"正在执行第 {current_iter}/{max_iter} 轮全网检索与混合知识提炼..."
                })
                
                res_data = await asyncio.to_thread(research_worker_node, state)
                state.update(res_data)
                
                self._emit_event(task_id, "facts_extracted", {
                    "total_citations": len(state.get("citations", [])),
                    "citations": state.get("citations", [])[-5:],
                    "outline": state.get("outline", [])
                })
                
                # Critic 评估节点
                self._emit_event(task_id, "thought", {"step": "critic", "message": "Critic 正在评估事实充实度与矛盾核验..."})
                critic_data = await asyncio.to_thread(critic_node, state)
                state.update(critic_data)
                
                self._emit_event(task_id, "critic_evaluated", {
                    "feedback": state.get("critic_feedback"),
                    "needs_more_research": state.get("needs_more_research"),
                    "iteration": state.get("iteration_count")
                })
                
                if not state.get("needs_more_research", False) or state.get("iteration_count", 1) > max_iter:
                    break

            # 4. Writer 撰写研报初稿阶段
            task_info["status"] = TaskStatus.WRITING
            self._emit_event(task_id, "thought", {"step": "writer", "message": "Writer 正在根据多轮事实撰写深度研报..."})
            
            writer_res = await asyncio.to_thread(synthesize_report_node, state)
            state.update(writer_res)
            
            # 5. Verifier 引用防幻觉校验阶段
            task_info["status"] = TaskStatus.VERIFYING
            self._emit_event(task_id, "thought", {"step": "verifier", "message": "Verifier 正在进行引用溯源 1:1 严格校验与防幻觉修正..."})
            
            verifier_res = await asyncio.to_thread(citation_verifier_node, state)
            state.update(verifier_res)
            
            # 6. 完成任务
            task_info["status"] = TaskStatus.COMPLETED
            self._emit_event(task_id, "completed", {
                "task_id": task_id,
                "final_report": state.get("final_report"),
                "citations": state.get("citations"),
                "outline": state.get("outline")
            })

        except asyncio.CancelledError:
            task_info["status"] = TaskStatus.CANCELLED
            self._emit_event(task_id, "cancelled", {"message": "任务已取消"})
        except Exception as e:
            task_info["status"] = TaskStatus.FAILED
            task_info["error"] = str(e)
            self._emit_event(task_id, "error", {"error": str(e)})

task_manager = TaskManager()
